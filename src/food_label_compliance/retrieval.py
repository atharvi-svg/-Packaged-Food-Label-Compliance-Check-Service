"""Retrieval contract and the default mock regulation retriever."""

import json
from pathlib import Path
from typing import Any, NotRequired, Protocol, TypedDict

from food_label_compliance.regulation_tools import search_regulations as search_mock_sources

DATA_DIR = Path(__file__).parent / "data"


class CitationMetadata(TypedDict):
    citation_id: str
    source_id: str
    regulation_name: str
    clause_id: str
    evidence_scope: NotRequired[str]


class RetrievedPassage(TypedDict):
    source_id: str
    regulation_name: str
    clause_id: str
    text: str
    citation_id: str
    citation_metadata: CitationMetadata
    source_type: str
    supports_rule_ids: list[str]
    claim_keywords: list[str]


class RegulationRetriever(Protocol):
    """Search and clause-lookup contract consumed by the agents.

    ``source_type=None`` searches all source types. Clause IDs must be globally
    unique, and citation IDs use the canonical ``source_id:clause_id`` form.
    """

    def search_regulations(
        self, query: str, source_type: str | None
    ) -> list[RetrievedPassage]:
        """Return source, regulation, clause, text, and citation metadata."""
        ...

    def lookup_clause(self, clause_id: str) -> RetrievedPassage | None:
        """Return a clause by its globally unique clause ID."""
        ...


class MockRegulationRetriever:
    """Search the bundled fictional mock corpus."""

    def __init__(self, sources: list[dict[str, Any]] | None = None) -> None:
        if sources is None:
            with (DATA_DIR / "mock_regulation_sources.json").open(
                encoding="utf-8"
            ) as data_file:
                payload: dict[str, Any] = json.load(data_file)
            sources = payload["sources"]
        self._sources = sources

    def search_regulations(
        self, query: str, source_type: str | None
    ) -> list[RetrievedPassage]:
        """Search mock sources and return normalized retriever records."""
        source_ids = (
            {
                source["source_id"]
                for source in self._sources
                if source["source_type"] == source_type
            }
            if source_type is not None
            else None
        )
        matches = search_mock_sources(query, self._sources, source_ids)
        return [self._to_record(match) for match in matches]

    def lookup_clause(self, clause_id: str) -> dict[str, Any] | None:
        """Look up a globally unique clause ID in the mock corpus."""
        for source in self._sources:
            for clause in source["clauses"]:
                if clause["clause_id"] == clause_id:
                    return self._to_record(
                        {
                            **clause,
                            "source_id": source["source_id"],
                            "source_type": source["source_type"],
                            "citation_id": (
                                f"{source['source_id']}:{clause['clause_id']}"
                            ),
                        }
                    )
        return None

    def _to_record(self, match: dict[str, Any]) -> RetrievedPassage:
        source_id = match["source_id"]
        source = next(
            source
            for source in self._sources
            if source["source_id"] == source_id
        )
        regulation_name = match.get(
            "regulation_name", source.get("name", source_id)
        )
        clause_id = match["clause_id"]
        citation_id = match["citation_id"]
        citation_metadata = {
            **match.get("citation_metadata", {}),
            "citation_id": citation_id,
            "source_id": source_id,
            "regulation_name": regulation_name,
            "clause_id": clause_id,
            "evidence_scope": match.get(
                "citation_metadata", {}
            ).get("evidence_scope", "fictional_mock_data_only"),
        }
        return {
            **match,
            "source_id": source_id,
            "regulation_name": regulation_name,
            "clause_id": clause_id,
            "text": match["text"],
            "citation_id": citation_id,
            "citation_metadata": citation_metadata,
        }
