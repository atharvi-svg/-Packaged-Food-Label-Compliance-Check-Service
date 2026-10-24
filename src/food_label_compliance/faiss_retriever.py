
"""Adapter connecting the FAISS index to the LangGraph retriever interface."""

import hashlib
from typing import Any

from retrieve import load_index, retrieve

from food_label_compliance.retrieval import RetrievedPassage


class FAISSRegulationRetriever:
    """Adapt FAISS search results to the workflow's retriever interface."""

    def __init__(self, vectorstore: Any = None) -> None:
        self.vectorstore = (
            vectorstore if vectorstore is not None else load_index()
        )
        self._passages: dict[str, RetrievedPassage] = {}

    def search_regulations(
        self,
        query: str,
        source_type: str | None = None,
    ) -> list[RetrievedPassage]:
        """Search FAISS and return passages in the expected format."""

        results = retrieve(self.vectorstore, query, top_k=5)
        passages: list[RetrievedPassage] = []

        for result in results:
            text = str(result.get("text", "")).strip()
            if not text:
                continue

            source = str(result.get("source", "unknown"))
            page = str(result.get("page", "unknown"))
            regulation_id = str(result.get("regulation_id", "OTHER"))

            digest = hashlib.sha256(
                f"{source}|{page}|{text}".encode("utf-8")
            ).hexdigest()[:12]

            source_id = f"{source}#page={page}"
            clause_id = f"passage-{digest}"
            citation_id = f"{source_id}:{clause_id}"

            # Do not claim that a retrieved passage supports a specific
            # rule unless that mapping has been explicitly validated.
            passage: RetrievedPassage = {
                "source_id": source_id,
                "regulation_name": regulation_id,
                "clause_id": clause_id,
                "text": text,
                "citation_id": citation_id,
                "citation_metadata": {
                    "citation_id": citation_id,
                    "source_id": source_id,
                    "regulation_name": regulation_id,
                    "clause_id": clause_id,
                    "evidence_scope": "retrieved_document_unverified",
                },
                "source_type": source_type or "labeling",
                "supports_rule_ids": [],
                "claim_keywords": [],
            }

            self._passages[clause_id] = passage
            passages.append(passage)

        return passages

    def lookup_clause(
        self,
        clause_id: str,
    ) -> RetrievedPassage | None:
        """Look up a passage retrieved earlier in this instance."""
        return self._passages.get(clause_id)
