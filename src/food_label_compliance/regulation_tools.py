"""Search and clause lookup for bundled mock regulation sources."""

import re
from typing import Any


def _tokens(value: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", value.casefold()))


def search_regulations(
    query: str,
    sources: list[dict[str, Any]],
    source_ids: set[str] | None = None,
) -> list[dict[str, Any]]:
    """Search mock source clauses by phrase or complete query-token match."""
    query_tokens = _tokens(query)
    normalized_query = " ".join(query.casefold().split())
    if not query_tokens:
        return []

    matches: list[dict[str, Any]] = []
    for source in sources:
        source_id = source["source_id"]
        if source_ids is not None and source_id not in source_ids:
            continue
        for clause in source["clauses"]:
            searchable_text = " ".join(
                [
                    source["name"],
                    clause["title"],
                    clause["text"],
                    *clause.get("keywords", []),
                    *clause.get("claim_keywords", []),
                ]
            )
            searchable_normalized = " ".join(searchable_text.casefold().split())
            searchable_tokens = _tokens(searchable_text)
            if (
                normalized_query in searchable_normalized
                or query_tokens.issubset(searchable_tokens)
            ):
                matches.append(
                    {
                        **clause,
                        "source_id": source_id,
                        "source_type": source["source_type"],
                        "citation_id": f"{source_id}:{clause['clause_id']}",
                    }
                )
    return matches


def lookup_clause(
    citation_id: str, sources: list[dict[str, Any]]
) -> dict[str, Any] | None:
    """Resolve a canonical source-and-clause citation to its mock passage."""
    for source in sources:
        source_id = source["source_id"]
        for clause in source["clauses"]:
            expected_citation = f"{source_id}:{clause['clause_id']}"
            if citation_id == expected_citation:
                return {
                    **clause,
                    "source_id": source_id,
                    "source_type": source["source_type"],
                    "citation_id": expected_citation,
                }
    return None
