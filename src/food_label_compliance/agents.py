"""Deterministic LangGraph nodes for mock label review."""

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


def _evidence_scope(passages: list[dict[str, Any]]) -> str:
    scopes = {
        passage.get("citation_metadata", {}).get("evidence_scope")
        for passage in passages
    }
    if scopes == {"fictional_mock_data_only"}:
        return "fictional_mock_data_only"
    return "retriever_provided"


def _lookup_search_result(
    retriever: RegulationRetriever, result: dict[str, Any]
) -> dict[str, Any] | None:
    passage = retriever.lookup_clause(result["clause_id"])
    if passage is None:
        return None
    if any(
        passage.get(key) != result.get(key)
        for key in ("source_id", "regulation_name", "clause_id", "citation_id")
    ):
        return None
    return passage


def _is_present(value: Any) -> bool:
    if isinstance(value, str):
        return bool(value.strip())
    return bool(value)


def _claim_keywords_match(claim_text: str, clause: dict[str, Any]) -> bool:
    claim_tokens = _tokens(claim_text)
    return any(
        _tokens(keyword).issubset(claim_tokens)
        for keyword in clause.get("claim_keywords", [])
        if _tokens(keyword)
    )


def _tokens(value: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", value.casefold()))


def compliance_investigator(
    state: ComplianceState,
    retriever: RegulationRetriever | None = None,
) -> dict[str, Any]:
    """Search the injected retriever for rules and separate claim sources."""
    if retriever is None:
        retriever = MockRegulationRetriever()
    label = state["product_label"]
    attempt = state["search_attempts"] + 1
    retrying = attempt > 1
    findings: list[Finding] = []
    retrieved = list(state["retrieved_passages"])
    retrieved_ids = {passage["citation_id"] for passage in retrieved}
    search_log = list(state["search_log"])
    missing_evidence: list[str] = []
    review_reasons: list[str] = []

    for rule in state["regulations"]:
        field = rule["field"]
        query = rule["requirement"]
        if retrying:
            query = field.replace("_", " ")
        search_results = retriever.search_regulations(query, None)
        grouped_results: dict[tuple[str, str], list[dict[str, Any]]] = {}
        for result in search_results:
            grouped_results.setdefault(
                (result["source_type"], result["source_id"]), []
            ).append(result)
        if not grouped_results:
            search_log.append(
                {
                    "attempt": attempt,
                    "query": query,
                    "source_ids": [],
                    "source_type": "all",
                    "target_id": rule["id"],
                    "matched_clause_ids": [],
                    "matched_citation_ids": [],
                }
            )
        for (source_type, source_id), source_results in grouped_results.items():
            search_log.append(
                {
                    "attempt": attempt,
                    "query": query,
                    "source_ids": [source_id],
                    "source_type": source_type,
                    "target_id": rule["id"],
                    "matched_clause_ids": [
                        result["clause_id"] for result in source_results
                    ],
                    "matched_citation_ids": [
                        result["citation_id"] for result in source_results
                    ],
                }
            )
        citations: list[str] = []
        for result in search_results:
            if rule["id"] not in result.get("supports_rule_ids", []):
                continue
            citation_id = result["citation_id"]
            passage = _lookup_search_result(retriever, result)
            if passage is None:
                continue
            citations.append(citation_id)
            if citation_id not in retrieved_ids:
                retrieved.append(passage)
                retrieved_ids.add(citation_id)

        if not citations:
            missing_evidence.append(rule["id"])
            review_reasons.append(
                f"No supporting mock passage was found for {rule['id']}."
            )
        value = label.get(field)
        present = _is_present(value)
        if not present:
            review_reasons.append(
                f"Label field {field} is absent or blank."
            )
        evidence_passages = [
            passage
            for passage in retrieved
            if passage["citation_id"] in citations
        ]
        evidence_scope = _evidence_scope(evidence_passages)
        status = "evidence_insufficient" if not citations else (
            "needs_review"
            if not present
            else "meets_mock_rule"
            if evidence_scope == "fictional_mock_data_only"
            else "field_present"
        )
        findings.append(
            {
                "target_id": rule["id"],
                "target_type": "rule",
                "requirement": rule["requirement"],
                "field": field,
                "status": status,
                "evidence": " ".join(
                    passage["text"]
                    for citation in citations
                    for passage in retrieved
                    if passage["citation_id"] == citation
                ),
                "citations": citations,
                "evidence_scope": evidence_scope,
            }
        )

    claims = label.get("claims", [])
    for index, claim in enumerate(claims):
        claim_id = str(claim.get("id", f"claim-{index + 1}"))
        claim_text = str(claim.get("text", "")).strip()
        if not claim_text:
            missing_evidence.append(claim_id)
            review_reasons.append(f"Claim {claim_id} has no searchable text.")
            findings.append(
                {
                    "target_id": claim_id,
                    "target_type": "claim",
                    "requirement": "Review a product claim against separate mock sources.",
                    "field": "claims",
                    "status": "evidence_insufficient",
                    "evidence": "",
                    "citations": [],
                    "evidence_scope": "fictional_mock_data_only",
                }
            )
            continue

        query = claim_text if not retrying else f"{claim_text} claim"
        citations = []
        for source_type in ("labeling", "claims"):
            search_results = retriever.search_regulations(query, source_type)
            source_results_by_id = {
                source_id: [
                    result
                    for result in search_results
                    if result["source_id"] == source_id
                ]
                for source_id in sorted(
                    {result["source_id"] for result in search_results}
                )
            }
            if not source_results_by_id:
                search_log.append(
                    {
                        "attempt": attempt,
                        "query": query,
                        "source_ids": [],
                        "source_type": source_type,
                        "target_id": claim_id,
                        "matched_clause_ids": [],
                        "matched_citation_ids": [],
                    }
                )
            for source_id, source_results in source_results_by_id.items():
                search_log.append(
                    {
                        "attempt": attempt,
                        "query": query,
                        "source_ids": [source_id],
                        "source_type": source_type,
                        "target_id": claim_id,
                        "matched_clause_ids": [
                            result["clause_id"] for result in source_results
                        ],
                        "matched_citation_ids": [
                            result["citation_id"] for result in source_results
                        ],
                    }
                )
            if source_type != "claims":
                continue
            for result in search_results:
                if not _claim_keywords_match(claim_text, result):
                    continue
                citation_id = result["citation_id"]
                passage = _lookup_search_result(retriever, result)
                if passage is None:
                    continue
                citations.append(citation_id)
                if citation_id not in retrieved_ids:
                    retrieved.append(passage)
                    retrieved_ids.add(citation_id)

        if not citations:
            missing_evidence.append(claim_id)
            review_reasons.append(
                f"No supporting mock claims passage was found for {claim_id}."
            )
        review_reasons.append(
            f"Verified regulatory evidence is unavailable for claim {claim_id}; "
            "retrieved passages are fictional mock data only."
        )
        findings.append(
            {
                "target_id": claim_id,
                "target_type": "claim",
                "requirement": (
                    f"Potentially separate regulation review for claim: {claim_text}"
                ),
                "field": "claims",
                "status": (
                    "evidence_insufficient"
                ),
                "evidence": " ".join(
                    passage["text"]
                    for citation in citations
                    for passage in retrieved
                    if passage["citation_id"] == citation
                ),
                "citations": citations,
                "evidence_scope": _evidence_scope(
                    [
                        passage
                        for passage in retrieved
                        if passage["citation_id"] in citations
                    ]
                ),
            }
        )

    return {
        "findings": findings,
        "retrieved_passages": retrieved,
        "search_log": search_log,
        "search_attempts": attempt,
        "missing_evidence": missing_evidence,
        "review_reasons": review_reasons,
    }


def evidence_verifier(state: ComplianceState) -> dict[str, Any]:
    """Verify every citation and its support against retrieved mock passages."""
    rules_by_id = {rule["id"]: rule for rule in state["regulations"]}
    retrieved_by_id = {
        passage["citation_id"]: passage
        for passage in state["retrieved_passages"]
    }
    label = state["product_label"]
    verification: list[Verification] = []
    review_reasons = list(state["review_reasons"])

    for finding in state["findings"]:
        target_id = finding["target_id"]
        cited_passages = [
            retrieved_by_id.get(citation)
            for citation in finding["citations"]
        ]
        citations_exist = bool(finding["citations"]) and all(
            passage is not None
            and passage.get("text")
            and passage.get("source_id")
            and passage.get("regulation_name")
            and passage.get("clause_id")
            and passage.get("citation_metadata", {}).get("citation_id")
            == citation
            and passage.get("citation_metadata", {}).get("source_id")
            == passage.get("source_id")
            and passage.get("citation_metadata", {}).get("regulation_name")
            == passage.get("regulation_name")
            and passage.get("citation_metadata", {}).get("clause_id")
            == passage.get("clause_id")
            and citation
            == f"{passage.get('source_id')}:{passage.get('clause_id')}"
            for citation, passage in zip(
                finding["citations"], cited_passages, strict=True
            )
        )
        passages = [
            passage for passage in cited_passages if passage is not None
        ]

        if finding["target_type"] == "rule":
            rule = rules_by_id.get(target_id)
            supported = bool(rule) and all(
                target_id in passage.get("supports_rule_ids", [])
                for passage in passages
            )
            if rule is None:
                expected_status = "evidence_insufficient"
            else:
                present = _is_present(label.get(rule["field"]))
                scope = _evidence_scope(passages)
                expected_status = (
                    "evidence_insufficient"
                    if not citations_exist
                    else "meets_mock_rule"
                    if present and scope == "fictional_mock_data_only"
                    else "field_present"
                    if present
                    else "needs_review"
                )
            requirement_matches = bool(rule) and (
                finding["field"] == rule["field"]
                and finding["requirement"] == rule["requirement"]
            )
            evidence_scope_matches = finding.get("evidence_scope") == _evidence_scope(passages)
        elif finding["target_type"] == "claim":
            supported = all(
                passage["source_type"] == "claims"
                and _claim_keywords_match(
                    next(
                        (
                            str(claim.get("text", ""))
                            for claim in label.get("claims", [])
                            if str(claim.get("id", ""))
                            == target_id
                        ),
                        "",
                    ),
                    passage,
                )
                for passage in passages
            )
            claim = next(
                (
                    claim
                    for index, claim in enumerate(label.get("claims", []))
                    if str(claim.get("id", f"claim-{index + 1}")) == target_id
                ),
                None,
            )
            expected_requirement = (
                f"Potentially separate regulation review for claim: "
                f"{str(claim.get('text', '')).strip()}"
                if claim is not None
                else ""
            )
            expected_status = "evidence_insufficient"
            requirement_matches = (
                claim is not None
                and finding["field"] == "claims"
                and finding["requirement"] == expected_requirement
            )
            evidence_scope_matches = (
                finding.get("evidence_scope") == "fictional_mock_data_only"
            )
        else:
            supported = False
            requirement_matches = False
            expected_status = "evidence_insufficient"
            evidence_scope_matches = False

        expected_evidence = " ".join(passage["text"] for passage in passages)
        checks_match = (
            citations_exist
            and supported
            and requirement_matches
            and evidence_scope_matches
            and finding["status"] == expected_status
            and finding["evidence"] == expected_evidence
        )
        if not checks_match:
            review_reasons.append(
                f"Evidence verification failed for {target_id}."
            )
        verification.append(
            {
                "target_id": target_id,
                "verified": checks_match,
                "explanation": (
                    "Citations were retrieved and support the finding."
                    if checks_match
                    else "A citation is missing, fabricated, or does not support the finding."
                ),
            }
        )

    verified_count = sum(item["verified"] for item in verification)
    review_count = sum(
        finding["status"] == "needs_review" for finding in state["findings"]
    )
    return {
        "verification": verification,
        "review_reasons": list(dict.fromkeys(review_reasons)),
        "summary": (
            f"{verified_count}/{len(verification)} findings verified; "
            f"{review_count} field(s) need review."
        ),
    }


def needs_retry(state: ComplianceState) -> str:
    """Allow one additional search pass when relevant evidence is missing."""
    if (
        state["missing_evidence"]
        and state["search_attempts"] < state["max_search_attempts"]
    ):
        return "retry"
    return "verify"


def needs_regulatory_review(state: ComplianceState) -> str:
    """Prevent completion when evidence is insufficient or unverified."""
    if (
        state["missing_evidence"]
        or len(state["verification"]) != len(state["findings"])
        or any(
            not item["verified"] for item in state["verification"]
        )
        or any(
            finding["status"] == "evidence_insufficient"
            for finding in state["findings"]
        )
        or any(
            finding["status"] == "needs_review"
            for finding in state["findings"]
        )
    ):
        return "review"
    return "done"


def regulatory_review(state: ComplianceState) -> dict[str, Any]:
    """Mark the result for human regulatory review without asserting a verdict."""
    return {
        "regulatory_review_required": True,
        "workflow_outcome": "regulatory_review",
        "summary": state["summary"],
    }
