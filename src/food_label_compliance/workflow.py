"""LangGraph workflow and sample data loaders."""

import json
from functools import partial
from pathlib import Path
from typing import Any

from langgraph.graph import END, START, StateGraph

from food_label_compliance.agents import (
    ComplianceState,
    compliance_investigator,
    evidence_verifier,
    needs_regulatory_review,
    needs_retry,
    regulatory_review,
)
from food_label_compliance.retrieval import (
    MockRegulationRetriever,
    RegulationRetriever,
)

DATA_DIR = Path(__file__).parent / "data"


def load_mock_regulations() -> list[dict[str, str]]:
    """Load the fictional regulation rules bundled with this project."""
    with (DATA_DIR / "mock_regulations.json").open(encoding="utf-8") as data_file:
        data: dict[str, Any] = json.load(data_file)
    return data["regulations"]


def load_sample_label() -> dict[str, Any]:
    """Load the example product label bundled with this project."""
    with (DATA_DIR / "sample_label.json").open(encoding="utf-8") as data_file:
        return json.load(data_file)


def load_source_of_protein_sample() -> dict[str, Any]:
    """Load the separate fictional test input for protein-claim review."""
    with (DATA_DIR / "sample_source_of_protein.json").open(
        encoding="utf-8"
    ) as data_file:
        return json.load(data_file)


def load_mock_regulation_sources() -> list[dict[str, Any]]:
    """Load fictional, non-authoritative passages for search and lookup."""
    with (DATA_DIR / "mock_regulation_sources.json").open(
        encoding="utf-8"
    ) as data_file:
        data: dict[str, Any] = json.load(data_file)
    return data["sources"]


def build_workflow(
    retriever: RegulationRetriever | None = None,
):
    """Build the workflow using the injected retriever or fictional mock default."""
    active_retriever = (
        retriever if retriever is not None else MockRegulationRetriever()
    )
    graph = StateGraph(ComplianceState)
    graph.add_node(
        "compliance_investigator",
        partial(compliance_investigator, retriever=active_retriever),
    )
    graph.add_node("evidence_verifier", evidence_verifier)
    graph.add_node("regulatory_review", regulatory_review)
    graph.add_edge(START, "compliance_investigator")
    graph.add_conditional_edges(
        "compliance_investigator",
        needs_retry,
        {"retry": "compliance_investigator", "verify": "evidence_verifier"},
    )
    graph.add_conditional_edges(
        "evidence_verifier",
        needs_regulatory_review,
        {"review": "regulatory_review", "done": END},
    )
    graph.add_edge("regulatory_review", END)
    return graph.compile()


def run_review(
    product_label: dict[str, Any],
    regulations: list[dict[str, str]] | None = None,
    regulation_sources: list[dict[str, Any]] | None = None,
    retriever: RegulationRetriever | None = None,
) -> ComplianceState:
    """Run review with a pluggable retriever or the bundled mock retriever."""
    if retriever is not None and regulation_sources is not None:
        raise ValueError("Pass retriever or regulation_sources, not both.")
    active_retriever = retriever
    if active_retriever is None:
        active_retriever = MockRegulationRetriever(regulation_sources)
    workflow = build_workflow(active_retriever)
    return workflow.invoke(
        {
            "product_label": product_label,
            "regulations": (
                load_mock_regulations() if regulations is None else regulations
            ),
            "findings": [],
            "retrieved_passages": [],
            "search_log": [],
            "search_attempts": 0,
            "max_search_attempts": 2,
            "missing_evidence": [],
            "verification": [],
            "regulatory_review_required": False,
            "review_reasons": [],
            "workflow_outcome": "completed",
            "summary": "",
        }
    )


def run_sample() -> ComplianceState:
    """Run the workflow on the included example label."""
    return run_review(load_sample_label())


def run_source_of_protein_sample() -> ComplianceState:
    """Run the normal review workflow on the protein-claim test label."""
    return run_review(load_source_of_protein_sample())
