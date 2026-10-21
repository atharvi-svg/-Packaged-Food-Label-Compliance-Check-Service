# Person 1 Retrieval Integration Handoff

This document describes the integration seam currently implemented for Person
1's real regulation retriever. The repository currently uses
`MockRegulationRetriever`; no real FSSAI retrieval backend is connected.

## Implemented interface

The protocol and typed passage record are defined in
`src/food_label_compliance/retrieval.py`:

```python
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
    def search_regulations(
        self, query: str, source_type: str | None
    ) -> list[RetrievedPassage]: ...

    def lookup_clause(self, clause_id: str) -> RetrievedPassage | None: ...
```

`CitationMetadata` requires:

```python
class CitationMetadata(TypedDict):
    citation_id: str
    source_id: str
    regulation_name: str
    clause_id: str
    evidence_scope: NotRequired[str]
```

Every returned passage must include the fields and types in `RetrievedPassage`,
including `source_id`, `regulation_name`, `clause_id`, `text`, and
`citation_metadata`. The current agents also require `source_type`,
`supports_rule_ids`, and `claim_keywords` for routing and deterministic
support checks.

## Citation and lookup rules

- Citation IDs use the canonical format `source_id:clause_id`.
- Clause IDs must be globally unique because `lookup_clause` accepts only a
  clause ID.
- `search_regulations(query, None)` searches all source types.
- Claim review searches by source type in this order: `"labeling"`, then
  `"claims"`.
- Each search result is resolved via `lookup_clause(result["clause_id"])`.
  The Investigator rejects it if the returned source ID, regulation name,
  clause ID, or citation ID differs from the search result.
- The Verifier checks the finding against the retrieved passage records saved
  by the Investigator and validates their citation metadata and support
  fields. It does not make an independent call to a real backend.

## Injecting a real implementation

`run_review` in `src/food_label_compliance/workflow.py` accepts the retriever
instance:

```python
result = run_review(product_label, retriever=my_retriever)
```

Do not pass `regulation_sources` at the same time as `retriever`; the workflow
raises `ValueError` if both are supplied. Omitting `retriever` continues to
use the default mock implementation.

Minimal adapter shape using the implemented types and workflow:

```python
from food_label_compliance.retrieval import (
    RegulationRetriever,
    RetrievedPassage,
)
from food_label_compliance.workflow import run_review


class PersonOneRetriever:
    def search_regulations(
        self, query: str, source_type: str | None
    ) -> list[RetrievedPassage]:
        # Connect Person 1's search/retrieval implementation here.
        raise NotImplementedError

    def lookup_clause(self, clause_id: str) -> RetrievedPassage | None:
        # Resolve the clause ID from Person 1's corpus here.
        raise NotImplementedError


my_retriever: RegulationRetriever = PersonOneRetriever()
result = run_review(product_label, retriever=my_retriever)
```

The method bodies above are placeholders, not a working real retriever. The
example connects Person 1's future implementation to the existing workflow
without changing the agents.

## Compatibility test

`tests/test_workflow.py::WorkflowTests::test_alternative_retriever_can_be_injected_into_agents`
injects `FakeRegulationRetriever` into `run_review` and exercises its search
and clause lookup through the LangGraph, then checks that the Verifier accepts
the returned passage. This proves compatibility with a fake implementation;
it does not test a real FSSAI source or backend.

## Still Person 1's responsibility

Person 1 must implement and validate:

1. Ingestion of the intended FSSAI documents and source metadata.
2. Document parsing and clause/chunk creation, including globally unique
   clause IDs and stable citation metadata.
3. Embedding generation and any embedding lifecycle/versioning.
4. Selection, setup, and operation of the vector database or other retrieval
   index.
5. Real regulation retrieval, including honoring `source_type` and returning
   passages in the required shape.
6. Evidence quality and provenance checks that establish whether retrieved
   content is an authoritative, current regulatory source.

The mock retriever and mock corpus remain the current default. No vector
database, real FSSAI ingestion, real embeddings, or real regulation search has
been implemented or connected by this handoff.
