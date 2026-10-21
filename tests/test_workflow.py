"""Tests for the mock LangGraph label-review workflow."""

import unittest
from typing import Any

from food_label_compliance.agents import evidence_verifier
from food_label_compliance.agents import needs_regulatory_review
from food_label_compliance.audit_report import build_audit_report
from food_label_compliance.regulation_tools import (
    lookup_clause,
    search_regulations,
)
from food_label_compliance.workflow import (
    load_mock_regulation_sources,
    load_mock_regulations,
    load_sample_label,
    load_source_of_protein_sample,
    run_review,
    run_sample,
    run_source_of_protein_sample,
)


class FakeRegulationRetriever:
    def __init__(self) -> None:
        self.search_calls: list[tuple[str, str | None]] = []
        self.lookup_calls: list[str] = []
        self.passage = {
            "source_id": "FAKE-SOURCE",
            "regulation_name": "Fictional test source",
            "clause_id": "FAKE-CLAUSE-1",
            "text": "Fake retrieval passage supports test rule.",
            "citation_id": "FAKE-SOURCE:FAKE-CLAUSE-1",
            "citation_metadata": {
                "citation_id": "FAKE-SOURCE:FAKE-CLAUSE-1",
                "source_id": "FAKE-SOURCE",
                "regulation_name": "Fictional test source",
                "clause_id": "FAKE-CLAUSE-1",
                "evidence_scope": "retriever_provided",
            },
            "source_type": "labeling",
            "supports_rule_ids": ["FAKE-RULE-1"],
            "claim_keywords": [],
        }

    def search_regulations(
        self, query: str, source_type: str | None
    ) -> list[dict[str, Any]]:
        self.search_calls.append((query, source_type))
        if query == "Fake test requirement" and source_type is None:
            return [self.passage]
        return []

    def lookup_clause(self, clause_id: str) -> dict[str, Any] | None:
        self.lookup_calls.append(clause_id)
        if clause_id == self.passage["clause_id"]:
            return self.passage
        return None


class WorkflowTests(unittest.TestCase):
    def test_alternative_retriever_can_be_injected_into_agents(self) -> None:
        retriever = FakeRegulationRetriever()
        result = run_review(
            load_sample_label(),
            regulations=[
                {
                    "id": "FAKE-RULE-1",
                    "requirement": "Fake test requirement",
                    "field": "statement_of_identity",
                }
            ],
            retriever=retriever,
        )

        self.assertEqual(retriever.search_calls, [("Fake test requirement", None)])
        self.assertEqual(retriever.lookup_calls, ["FAKE-CLAUSE-1"])
        self.assertEqual(
            result["retrieved_passages"][0]["source_id"], "FAKE-SOURCE"
        )
        self.assertTrue(result["verification"][0]["verified"])
        self.assertEqual(result["findings"][0]["status"], "field_present")
        self.assertEqual(result["workflow_outcome"], "completed")

    def test_source_of_protein_sample_runs_full_workflow_and_escalates(
        self,
    ) -> None:
        result = run_source_of_protein_sample()
        report = build_audit_report(result)
        label = load_source_of_protein_sample()

        self.assertEqual(report["input"]["label"], label)
        self.assertEqual(
            report["input"]["label"]["nutrition"]["protein"],
            "10 g per 100 g",
        )
        self.assertEqual(
            report["input"]["detected_claims"],
            [{"id": "CLAIM-SOURCE-OF-PROTEIN", "text": "source of protein"}],
        )

        claim_searches = [
            search
            for search in report["search_history"]
            if search["target_id"] == "CLAIM-SOURCE-OF-PROTEIN"
            and search["attempt"] == 1
        ]
        self.assertEqual(
            [
                (search["source_type"], search["source_id"], search["query"])
                for search in claim_searches
            ],
            [
                ("labeling", "MOCK-LABELING", "source of protein"),
                ("claims", "MOCK-CLAIMS", "source of protein"),
            ],
        )
        self.assertEqual(
            claim_searches[0]["matched_clause_ids"], ["MOCK-CLAIM-001"]
        )
        self.assertEqual(
            claim_searches[0]["matched_citation_ids"],
            ["MOCK-LABELING:MOCK-CLAIM-001"],
        )
        self.assertEqual(
            claim_searches[1]["matched_clause_ids"], ["CLAIM-001"]
        )
        self.assertEqual(
            claim_searches[1]["matched_citation_ids"],
            ["MOCK-CLAIMS:CLAIM-001"],
        )

        claim_finding = next(
            finding
            for finding in report["findings"]
            if finding["target_id"] == "CLAIM-SOURCE-OF-PROTEIN"
        )
        self.assertEqual(claim_finding["status"], "evidence_insufficient")
        self.assertTrue(report["human_regulatory_review_required"])
        self.assertEqual(report["final_outcome"], "regulatory_review")
        self.assertIn(
            "Verified regulatory evidence is unavailable",
            report["escalation_reason"],
        )
        self.assertIn("fictional mock data", report["mock_data_notice"])

    def test_audit_report_contains_workflow_evidence_and_review_details(
        self,
    ) -> None:
        label = load_sample_label()
        label["claims"] = [{"id": "CLAIM-A", "text": "source of protein"}]

        report = build_audit_report(run_review(label))

        self.assertEqual(report["input"]["label"], label)
        self.assertEqual(report["input"]["detected_claims"], label["claims"])
        claim_searches = [
            entry
            for entry in report["search_history"]
            if entry["target_id"] == "CLAIM-A"
        ]
        self.assertEqual(
            [(entry["source_id"], entry["query"]) for entry in claim_searches],
            [
                ("MOCK-LABELING", "source of protein"),
                ("MOCK-CLAIMS", "source of protein"),
            ],
        )
        self.assertTrue(
            all(
                "matched_clause_ids" in entry
                and "matched_citation_ids" in entry
                for entry in report["search_history"]
            )
        )
        self.assertTrue(
            all(
                finding["verification_status"] == "verified"
                and finding["verification_explanation"]
                for finding in report["findings"]
            )
        )
        self.assertIn(
            "MOCK-CLAIMS:CLAIM-001",
            [
                clause["citation_id"]
                for clause in report["retrieved_clauses"]
            ],
        )
        self.assertEqual(report["retry_count"], 0)
        self.assertTrue(report["human_regulatory_review_required"])
        self.assertEqual(report["final_outcome"], "regulatory_review")
        self.assertIn("Verified regulatory evidence is unavailable", report["escalation_reason"])
        self.assertIn("fictional mock data", report["mock_data_notice"])

    def test_audit_report_never_labels_unverified_finding_compliant(
        self,
    ) -> None:
        result = run_review(load_sample_label())
        findings = [dict(finding) for finding in result["findings"]]
        findings[0]["citations"] = ["MOCK-LABELING:MADE-UP"]
        state = dict(result)
        state["findings"] = findings
        state["verification"] = evidence_verifier(state)["verification"]

        report = build_audit_report(state)

        self.assertEqual(report["findings"][0]["status"], "unverified")
        self.assertEqual(
            report["findings"][0]["verification_status"], "unverified"
        )

    def test_sample_workflow_checks_and_verifies_each_rule(self) -> None:
        result = run_sample()

        self.assertEqual(len(result["findings"]), 5)
        self.assertEqual(len(result["verification"]), 5)
        self.assertTrue(all(item["verified"] for item in result["verification"]))
        allergen_finding = next(
            finding
            for finding in result["findings"]
            if finding["target_id"] == "MOCK-004"
        )
        self.assertEqual(allergen_finding["status"], "needs_review")
        self.assertEqual(
            result["summary"], "5/5 findings verified; 1 field(s) need review."
        )

    def test_searches_across_sources_and_looks_up_a_claim_clause(self) -> None:
        sources = load_mock_regulation_sources()

        results = search_regulations("fictional mock passage", sources)
        claim_results = search_regulations("high protein", sources)
        clause = lookup_clause(claim_results[0]["citation_id"], sources)

        self.assertEqual(
            {result["source_id"] for result in results},
            {"MOCK-LABELING", "MOCK-CLAIMS"},
        )
        self.assertEqual(claim_results[0]["source_id"], "MOCK-CLAIMS")
        self.assertIsNotNone(clause)
        self.assertIn("Fictional mock passage", clause["text"])

    def test_source_of_protein_searches_labeling_then_claims_and_escalates(
        self,
    ) -> None:
        label = load_sample_label()
        label["claims"] = [{"id": "CLAIM-A", "text": "source of protein"}]

        result = run_review(label)

        claim_finding = next(
            finding
            for finding in result["findings"]
            if finding["target_id"] == "CLAIM-A"
        )
        self.assertEqual(claim_finding["status"], "evidence_insufficient")
        self.assertEqual(
            claim_finding["evidence_scope"], "fictional_mock_data_only"
        )
        self.assertEqual(
            claim_finding["citations"], ["MOCK-CLAIMS:CLAIM-001"]
        )
        claim_searches = [
            entry
            for entry in result["search_log"]
            if entry.get("target_id") == "CLAIM-A"
        ]
        self.assertEqual(
            [entry["source_type"] for entry in claim_searches],
            ["labeling", "claims"],
        )
        self.assertEqual(
            [entry["source_ids"] for entry in claim_searches],
            [["MOCK-LABELING"], ["MOCK-CLAIMS"]],
        )
        self.assertEqual(
            [entry["attempt"] for entry in claim_searches], [1, 1]
        )
        self.assertEqual(
            [entry["query"] for entry in claim_searches],
            ["source of protein", "source of protein"],
        )
        self.assertNotEqual(claim_finding["status"], "meets_mock_rule")
        self.assertTrue(result["regulatory_review_required"])
        self.assertEqual(result["workflow_outcome"], "regulatory_review")

    def test_missing_evidence_retries_once_then_escalates(self) -> None:
        result = run_review(load_sample_label(), regulation_sources=[])

        self.assertEqual(result["search_attempts"], 2)
        self.assertTrue(result["missing_evidence"])
        self.assertTrue(result["regulatory_review_required"])
        self.assertEqual(result["workflow_outcome"], "regulatory_review")

    def test_verifier_rejects_a_fabricated_citation(self) -> None:
        label = load_sample_label()
        regulations = load_mock_regulations()
        workflow_result = run_review(label, regulations=regulations)
        state = dict(workflow_result)
        findings = [dict(finding) for finding in workflow_result["findings"]]
        findings[0]["citations"] = ["MOCK-LABELING:MADE-UP"]
        state["findings"] = findings

        verification_result = evidence_verifier(state)

        self.assertFalse(verification_result["verification"][0]["verified"])
        state["verification"] = verification_result["verification"]
        self.assertEqual(needs_regulatory_review(state), "review")

        unrelated_citation = findings[1]["citations"][0]
        findings[0]["citations"] = [unrelated_citation]
        cited_passage = next(
            passage
            for passage in state["retrieved_passages"]
            if passage["citation_id"] == unrelated_citation
        )
        findings[0]["evidence"] = cited_passage["text"]
        state["findings"] = findings

        verification_result = evidence_verifier(state)

        self.assertFalse(verification_result["verification"][0]["verified"])
        state["verification"] = verification_result["verification"]
        self.assertEqual(needs_regulatory_review(state), "review")

    def test_incomplete_verification_cannot_finish_as_completed(self) -> None:
        label = load_sample_label()
        result = run_review(label)
        result["verification"] = result["verification"][:-1]

        self.assertEqual(needs_regulatory_review(result), "review")


if __name__ == "__main__":
    unittest.main()
