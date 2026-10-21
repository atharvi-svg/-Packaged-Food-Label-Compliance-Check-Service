"""Structured, mock-data-scoped audit reports for workflow runs."""

from typing import Any


def build_audit_report(state: dict[str, Any]) -> dict[str, Any]:
    """Build an audit report without changing the LangGraph state."""
    verifications = {
        item["target_id"]: item for item in state["verification"]
    }
    findings = []
    for finding in state["findings"]:
        verification = verifications.get(finding["target_id"])
        verified = bool(verification and verification["verified"])
        findings.append(
            {
                "target_id": finding["target_id"],
                "target_type": finding["target_type"],
                "field": finding["field"],
                "requirement": finding["requirement"],
                "status": finding["status"] if verified else "unverified",
                "verification_status": (
                    "verified" if verified else "unverified"
                ),
                "verification_explanation": (
                    verification["explanation"]
                    if verification
                    else "No verification result was produced."
                ),
                "citations": list(finding["citations"]),
                "evidence_scope": finding.get(
                    "evidence_scope", "retriever_provided"
                ),
            }
        )

    claims = state["product_label"].get("claims", [])
    return {
        "report_type": "food_label_workflow_audit",
        "mock_data_notice": (
            "All bundled regulation rules and passages are fictional mock data. "
            "They do not establish legal compliance or represent FSSAI requirements."
        ),
        "input": {
            "label": state["product_label"],
            "detected_claims": claims,
        },
        "search_history": [
            {
                "attempt": search["attempt"],
                "query": search["query"],
                "source_id": source_id,
                "source_type": search["source_type"],
                "target_id": search.get("target_id"),
                "matched_clause_ids": search.get("matched_clause_ids", []),
                "matched_citation_ids": search.get(
                    "matched_citation_ids", []
                ),
            }
            for search in state["search_log"]
            for source_id in search["source_ids"]
        ],
        "retrieved_clauses": [
            {
                "source_id": passage["source_id"],
                "regulation_name": passage["regulation_name"],
                "clause_id": passage["clause_id"],
                "text": passage["text"],
                "citation_id": passage["citation_id"],
                "citation_metadata": passage["citation_metadata"],
                "evidence_scope": passage.get("citation_metadata", {}).get(
                    "evidence_scope", "retriever_provided"
                ),
            }
            for passage in state["retrieved_passages"]
        ],
        "findings": findings,
        "retry_count": max(0, state["search_attempts"] - 1),
        "search_attempt_count": state["search_attempts"],
        "human_regulatory_review_required": state[
            "regulatory_review_required"
        ],
        "final_outcome": state["workflow_outcome"],
        "escalation_reason": (
            " ".join(state["review_reasons"])
            if state["regulatory_review_required"]
            else None
        ),
        "summary": state["summary"],
    }
