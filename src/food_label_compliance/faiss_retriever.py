
"""Adapter connecting Person 1's FAISS retriever to Person 2's workflow."""

from typing import Any

from retrieve import load_index, retrieve

from food_label_compliance.retrieval import RetrievedPassage


class FAISSRegulationRetriever:
    """Adapt FAISS search results to the RegulationRetriever interface."""

    def __init__(self, vectorstore: Any = None) -> None:
        self.vectorstore = vectorstore if vectorstore is not None else load_index()
        self._passages: dict[str, RetrievedPassage] = {}

    def search_regulations(
        self,
        query: str,
        source_type: str | None = None,
    ) -> list[RetrievedPassage]:
        results = retrieve(self.vectorstore, query, top_k=5)
        passages: list[RetrievedPassage] = []

        for result in results:
            source = str(result.get("source", "unknown"))
            page = str(result.get("page", "unknown"))
            text = str(result.get("text", "")).strip()

            if not text:
                continue

            # Use a stable identifier based on the document and page.
            source_id = f"{source}#page={page}"
            clause_id = "retrieved-passage"
            citation_id = f"{source_id}:{clause_id}"

            passage: RetrievedPassage = {
                "source_id": source_id,
                "regulation_name": source,
                "clause_id": clause_id,
                "text": text,
                "citation_id": citation_id,
                "citation_metadata": {
                    "citation_id": citation_id,
                    "source_id": source_id,
                    "regulation_name": source,
                    "clause_id": clause_id,
                    "evidence_scope": "retrieved_regulatory_document",
                },
                "source_type": "labeling",
                "supports_rule_ids": [],
                "claim_keywords": [],
            }

            self._passages[citation_id] = passage
            passages.append(passage)

        return passages

    def lookup_clause(self, clause_id: str) -> RetrievedPassage | None:
        return self._passages.get(clause_id)
