
"""LangGraph agents for food-label compliance review.

Mock evidence is verified using explicit rule mappings.
FAISS passages can be retrieved and recorded as context, but are not
treated as verified regulatory support without validated mappings.
"""

import re
from typing import Any, TypedDict

from food_label_compliance.retrieval import (
    MockRegulationRetriever,
    RegulationRetriever,
)


class Finding(TypedDict):
    target_id: str
    target_type: str
    requirement: str
    field: str
    status: str
    evidence: str
    citations: list[str]
    evidence_scope: str


class Verification(TypedDict):
    target_id: str
    verified: bool
    explanation: str


class ComplianceState(TypedDict):
    product_label: dict[str, Any]
    regulations: list[dict[str, str]]
    findings: list[Finding]
    retrieved_passages: list[dict[str, Any]]
    search_log: list[dict[str, Any]]
    search_attempts: int
    max_search_attempts: int
    missing_evidence: list[str]
    verification: list[Verification]
    regulatory_review_required: bool
    review_reasons: list[str]
    workflow_outcome: str
    summary: str


def _is_mock_passage(passage: dict[str, Any]) -> bool:
    """Return True only for explicitly identified fictional mock evidence."""
    return (
        passage.get("citation_metadata", {}).get("evidence_scope")
        == "fictional_mock_data_only"
    )


def _evidence_scope(passages: list[dict[str, Any]]) -> str:
    """Describe the evidence scope without overstating its authority."""
    if passages and all(_is_mock_passage(p) for p in passages):
        return "fictional_mock_data_only"

    if passages:
        return "retriever_provided_unverified"

    return "no_verified_evidence"


def _lookup_search_result(
    retriever: RegulationRetriever,
    result: dict[str, Any],
) -> dict[str, Any] | None:
    """Resolve a search result and verify its identifying metadata."""
    clause_id = result.get("clause_id")
    if not clause_id:
        return None

    passage = retriever.lookup_clause(clause_id)
    if passage is None:
        return None

    keys = (
        "source_id",
        "regulation_name",
        "clause_id",
        "citation_id",
    )

    if any(passage.get(key) != result.get(key) for key in keys):
        return None

    metadata = passage.get("citation_metadata", {})
    if (
        metadata.get("citation_id") != passage.get("citation_id")
        or metadata.get("source_id") != passage.get("source_id")
        or metadata.get("regulation_name")
        != passage.get("regulation_name")
        or metadata.get("clause_id") != passage.get("clause_id")
    ):
        return None

    return passage


def _is_present(value: Any) -> bool:
    """Check whether a label field contains a non-empty value."""
    if isinstance(value, str):
        return bool(value.strip())
    return bool(value)


def _tokens(value: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", value.casefold()))


def _claim_keywords_match(
    claim_text: str,
    passage: dict[str, Any],
) -> bool:
    """Match claim keywords supplied by the retriever."""
    claim_tokens = _tokens(claim_text)

    return any(
        _tokens(keyword).issubset(claim_tokens)
        for keyword in passage.get("claim_keywords", [])
        if _tokens(keyword)
    )


def _record_search(
    search_log: list[dict[str, Any]],
    attempt: int,
    query: str,
    target_id: str,
    source_type: str,
    results: list[dict[str, Any]],
) -> None:
    """Record the results of a retrieval attempt."""
    grouped: dict[str, list[dict[str, Any]]] = {}

    for result in results:
        source_id = str(result.get("source_id", "unknown"))
        grouped.setdefault(source_id, []).append(result)

    if not grouped:
        search_log.append(
            {
                "attempt": attempt,
                "query": query,
                "source_ids": [],
                "source_type": source_type,
                "target_id": target_id,
                "matched_clause_ids": [],
                "matched_citation_ids": [],
            }
        )
        return

    for source_id, source_results in grouped.items():
        search_log.append(
            {
                "attempt": attempt,
                "query": query,
                "source_ids": [source_id],
                "source_type": source_type,
                "target_id": target_id,
                "matched_clause_ids": [
                    result.get("clause_id", "")
                    for result in source_results
                ],
                "matched_citation_ids": [
                    result.get("citation_id", "")
                    for result in source_results
                ],
            }
        )


def _retain_context(
    passage: dict[str, Any],
    retrieved: list[dict[str, Any]],
    retrieved_ids: set[str],
) -> None:
    """Retain a passage for investigation without asserting compliance."""
    citation_id = passage.get("citation_id")
    if not citation_id or citation_id in retrieved_ids:
        return

    retrieved.append(passage)
    retrieved_ids.add(citation_id)


def compliance_investigator(
    state: ComplianceState,
    retriever: RegulationRetriever | None = None,
) -> dict[str, Any]:
    """Investigate label fields using mock or injected retrieval."""
    if retriever is None:
        retriever = MockRegulationRetriever()

    label = state["product_label"]
    attempt = state["search_attempts"] + 1
    retrying = attempt > 1

    findings: list[Finding] = []
    retrieved = list(state["retrieved_passages"])
    retrieved_ids = {
        p.get("citation_id")
        for p in retrieved
        if p.get("citation_id")
    }
    search_log = list(state["search_log"])
    missing_evidence: list[str] = []
    review_reasons: list[str] = []

    # Review required label fields.
    for rule in state["regulations"]:
        rule_id = rule["id"]
        field = rule["field"]
        query = (
            field.replace("_", " ")
            if retrying
            else rule["requirement"]
        )

        search_results = retriever.search_regulations(query, None)

        _record_search(
            search_log,
            attempt,
            query,
            rule_id,
            "all",
            search_results,
        )

        verified_mock_passages: list[dict[str, Any]] = []
        unverified_context: list[dict[str, Any]] = []

        for result in search_results:
            passage = _lookup_search_result(retriever, result)
            if passage is None:
                continue

            _retain_context(passage, retrieved, retrieved_ids)

            if _is_mock_passage(passage):
                # Mock rules require an explicit rule-to-passage mapping.
                if rule_id in passage.get("supports_rule_ids", []):
                    verified_mock_passages.append(passage)
            else:
                # FAISS relevance is useful context, not proof of support.
                unverified_context.append(passage)

        citations = list(
            dict.fromkeys(
                p["citation_id"] for p in verified_mock_passages
            )
        )

        present = _is_present(label.get(field))

        if not present:
            review_reasons.append(
                f"Label field {field} is absent or blank."
            )

        if citations:
            evidence_passages = verified_mock_passages
            status = "meets_mock_rule" if present else "needs_review"
            scope = "fictional_mock_data_only"
        else:
            evidence_passages = unverified_context
            status = "evidence_insufficient"
            scope = (
                "retriever_provided_unverified"
                if unverified_context
                else "no_verified_evidence"
            )
            missing_evidence.append(rule_id)

            if unverified_context:
                review_reasons.append(
                    f"Retrieved passages for {rule_id}, but no validated "
                    "rule-to-passage mapping is available."
                )
            else:
                review_reasons.append(
                    f"No verified supporting evidence was found for {rule_id}."
                )

        findings.append(
            {
                "target_id": rule_id,
                "target_type": "rule",
                "requirement": rule["requirement"],
                "field": field,
                "status": status,
                "evidence": " ".join(
                    p.get("text", "") for p in evidence_passages
                ),
                # Unverified FAISS passages are context only; they are
                # intentionally not represented as supporting citations.
                "citations": citations,
                "evidence_scope": scope,
            }
        )

    # Review product claims against the separate claims source.
    for index, claim in enumerate(label.get("claims", [])):
        claim_id = str(claim.get("id", f"claim-{index + 1}"))
        claim_text = str(claim.get("text", "")).strip()

        if not claim_text:
            missing_evidence.append(claim_id)
            review_reasons.append(
                f"Claim {claim_id} has no searchable text."
            )
            findings.append(
                {
                    "target_id": claim_id,
                    "target_type": "claim",
                    "requirement": (
                        "Review the product claim against relevant sources."
                    ),
                    "field": "claims",
                    "status": "evidence_insufficient",
                    "evidence": "",
                    "citations": [],
                    "evidence_scope": "no_verified_evidence",
                }
            )
            continue

        query = (
            f"{claim_text} claim"
            if retrying
            else claim_text
        )

        claim_passages: list[dict[str, Any]] = []
        unverified_claim_context: list[dict[str, Any]] = []

        for source_type in ("labeling", "claims"):
            results = retriever.search_regulations(query, source_type)

            _record_search(
                search_log,
                attempt,
                query,
                claim_id,
                source_type,
                results,
            )

            # Claim-specific support is only accepted from the claims source.
            if source_type != "claims":
                for result in results:
                    passage = _lookup_search_result(retriever, result)
                    if passage is not None:
                        _retain_context(
                            passage, retrieved, retrieved_ids
                        )
                continue

            for result in results:
                passage = _lookup_search_result(retriever, result)
                if passage is None:
                    continue

                _retain_context(passage, retrieved, retrieved_ids)

                if (
                    _is_mock_passage(passage)
                    and passage.get("source_type") == "claims"
                    and _claim_keywords_match(claim_text, passage)
                ):
                    claim_passages.append(passage)
                elif not _is_mock_passage(passage):
                    unverified_claim_context.append(passage)

        claim_passages = list(
            {
                p["citation_id"]: p
                for p in claim_passages
            }.values()
        )

        if claim_passages:
            citations = [
                p["citation_id"] for p in claim_passages
            ]
            evidence = " ".join(
                p.get("text", "") for p in claim_passages
            )
            scope = "fictional_mock_data_only"
        else:
            citations = []
            evidence = " ".join(
                p.get("text", "")
                for p in unverified_claim_context
            )
            scope = (
                "retriever_provided_unverified"
                if unverified_claim_context
                else "no_verified_evidence"
            )
            missing_evidence.append(claim_id)
            review_reasons.append(
                f"No verified claim-specific evidence was found for {claim_id}."
            )

        # This workflow does not determine legal compliance of claims.
        findings.append(
            {
                "target_id": claim_id,
                "target_type": "claim",
                "requirement": (
                    f"Review product claim: {claim_text}"
                ),
                "field": "claims",
                "status": "evidence_insufficient",
                "evidence": evidence,
                "citations": citations,
                "evidence_scope": scope,
            }
        )

        review_reasons.append(
            f"Claim {claim_id} requires human review; this workflow "
            "does not independently establish regulatory compliance."
        )

    return {
        "findings": findings,
        "retrieved_passages": retrieved,
        "search_log": search_log,
        "search_attempts": attempt,
        "missing_evidence": list(dict.fromkeys(missing_evidence)),
        "review_reasons": list(dict.fromkeys(review_reasons)),
    }


def evidence_verifier(
    state: ComplianceState,
) -> dict[str, Any]:
    """Verify citations, rule mappings, and finding consistency."""
    rules_by_id = {
        rule["id"]: rule for rule in state["regulations"]
    }
    retrieved_by_id = {
        passage["citation_id"]: passage
        for passage in state["retrieved_passages"]
        if passage.get("citation_id")
    }
    label = state["product_label"]
    verification: list[Verification] = []
    review_reasons = list(state["review_reasons"])

    claims_by_id = {
        str(claim.get("id", f"claim-{index + 1}")): claim
        for index, claim in enumerate(label.get("claims", []))
    }

    for finding in state["findings"]:
        target_id = finding["target_id"]
        citations = finding["citations"]

        cited_passages = [
            retrieved_by_id.get(citation)
            for citation in citations
        ]

        # Citation IDs must resolve to consistent passage metadata.
        citations_valid = bool(citations) and all(
            passage is not None
            and bool(passage.get("text"))
            and bool(passage.get("source_id"))
            and bool(passage.get("clause_id"))
            and passage.get("citation_metadata", {}).get(
                "citation_id"
            ) == citation
            and passage.get("citation_metadata", {}).get(
                "source_id"
            ) == passage.get("source_id")
            and passage.get("citation_metadata", {}).get(
                "regulation_name"
            ) == passage.get("regulation_name")
            and passage.get("citation_metadata", {}).get(
                "clause_id"
            ) == passage.get("clause_id")
            and citation == (
                f"{passage.get('source_id')}:"
                f"{passage.get('clause_id')}"
            )
            for citation, passage in zip(
                citations, cited_passages, strict=True
            )
        )

        passages = [
            passage
            for passage in cited_passages
            if passage is not None
        ]

        if finding["target_type"] == "rule":
            rule = rules_by_id.get(target_id)
            present = (
                _is_present(label.get(rule["field"]))
                if rule is not None
                else False
            )

            # Never accept FAISS passages as verified support merely
            # because they were retrieved for a rule query.
            supported = (
                rule is not None
                and citations_valid
                and all(
                    _is_mock_passage(passage)
                    and target_id
                    in passage.get("supports_rule_ids", [])
                    for passage in passages
                )
            )

            requirement_matches = (
                rule is not None
                and finding["field"] == rule["field"]
                and finding["requirement"] == rule["requirement"]
            )

            if supported and requirement_matches:
                expected_status = (
                    "meets_mock_rule" if present else "needs_review"
                )
                expected_scope = "fictional_mock_data_only"
                expected_evidence = " ".join(
                    passage["text"] for passage in passages
                )
            else:
                expected_status = "evidence_insufficient"
                expected_scope = (
                    "retriever_provided_unverified"
                    if finding["evidence_scope"]
                    == "retriever_provided_unverified"
                    else "no_verified_evidence"
                )
                expected_evidence = finding["evidence"]

            checks_match = (
                supported
                and requirement_matches
                and finding["status"] == expected_status
                and finding["evidence_scope"] == expected_scope
                and finding["evidence"] == expected_evidence
            )

        elif finding["target_type"] == "claim":
            claim = claims_by_id.get(target_id)
            expected_requirement = (
                f"Review product claim: "
                f"{str(claim.get('text', '')).strip()}"
                if claim is not None
                else ""
            )

            supported = (
                claim is not None
                and citations_valid
                and all(
                    _is_mock_passage(passage)
                    and passage.get("source_type") == "claims"
                    and _claim_keywords_match(
                        str(claim.get("text", "")), passage
                    )
                    for passage in passages
                )
            )

            requirement_matches = (
                claim is not None
                and finding["field"] == "claims"
                and finding["requirement"] == expected_requirement
            )

            # Claims are deliberately not marked compliant automatically.
            checks_match = (
                supported
                and requirement_matches
                and finding["status"] == "evidence_insufficient"
                and finding["evidence_scope"]
                == "fictional_mock_data_only"
                and finding["evidence"]
                == " ".join(p["text"] for p in passages)
            )

        else:
            checks_match = False

        if not checks_match:
            review_reasons.append(
                f"Evidence verification failed or remains incomplete "
                f"for {target_id}."
            )

        verification.append(
            {
                "target_id": target_id,
                "verified": checks_match,
                "explanation": (
                    "Evidence passed the workflow's structural and "
                    "mapping checks; this is not independent legal advice."
                    if checks_match
                    else "Evidence is missing, unverified, inconsistently "
                    "cited, or lacks an explicit rule mapping."
                ),
            }
        )

    verified_count = sum(
        item["verified"] for item in verification
    )
    review_count = sum(
        finding["status"] in {
            "needs_review",
            "evidence_insufficient",
        }
        for finding in state["findings"]
    )

    return {
        "verification": verification,
        "review_reasons": list(dict.fromkeys(review_reasons)),
        "summary": (
            f"{verified_count}/{len(verification)} findings passed "
            f"evidence checks; {review_count} finding(s) require "
            "review or additional evidence."
        ),
    }


def needs_retry(state: ComplianceState) -> str:
    """Allow one additional retrieval attempt for missing evidence."""
    if (
        state["missing_evidence"]
        and state["search_attempts"] < state["max_search_attempts"]
    ):
        return "retry"

    return "verify"


def needs_regulatory_review(state: ComplianceState) -> str:
    """Route uncertain, incomplete, or unverified findings to review."""
    if (
        state["missing_evidence"]
        or len(state["verification"]) != len(state["findings"])
        or any(
            not item["verified"]
            for item in state["verification"]
        )
        or any(
            finding["status"] in {
                "evidence_insufficient",
                "needs_review",
            }
            for finding in state["findings"]
        )
    ):
        return "review"

    return "done"


def regulatory_review(
    state: ComplianceState,
) -> dict[str, Any]:
    """Flag the result for human review without asserting compliance."""
    return {
        "regulatory_review_required": True,
        "workflow_outcome": "regulatory_review",
        "review_reasons": list(
            dict.fromkeys(state["review_reasons"])
        ),
        "summary": state["summary"],
    }
