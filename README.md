# Food Label Compliance — Person 2

This project implements two LangGraph agents and a mock-source retrieval
workflow:

1. **Compliance Investigator** searches multiple mock sources for each mock
   rule. When the label includes a product claim, it searches the labeling
   source and then the separate mock claims source, recording both searches.
   Because the available passages are fictional, the claim is marked
   `evidence_insufficient` and sent for regulatory review, not judged compliant.
2. **Evidence Verifier** checks that every citation points to a retrieved
   passage and that the passage supports the finding.
3. If evidence is missing, the Investigator gets one bounded retry. The graph
   escalates unverified findings, unavailable evidence, and potentially
   cross-regulation claims to a regulatory-review outcome.

The workflow is deterministic and uses no API keys or external services.
Every regulation source and passage in this starter is clearly labelled
fictional mock data for development and testing. The mock rules do not establish
legal compliance, are not legal advice, and are not FSSAI requirements.

## Run

From the project root in PowerShell:

```powershell
.\venv\Scripts\python.exe -m pip install -e .
.\venv\Scripts\python.exe -m food_label_compliance
```

Run the separate `"source of protein"` label through the same workflow and
print its audit report with:

```powershell
.\venv\Scripts\python.exe -m food_label_compliance --sample source-of-protein
```

If you use a different Python environment, activate it first and use
`python -m pip install -e .` followed by
`python -m food_label_compliance`.

The CLI prints a structured JSON audit report with the input label and claims,
per-source search history, matched and retrieved clause/citation IDs, finding
verification explanations, retry count, review status, and escalation reason.
Unverified findings are presented as `unverified`, not as passing findings.
The sample label intentionally omits an allergen declaration so the report
demonstrates a `needs_review` result and regulatory-review escalation. To
exercise a separate-source claim search in code, include a claim in the label,
for example `{"claims": [{"id": "CLAIM-A", "text": "source of protein"}]}`.
This trigger is tested only against fictional mock data, not real requirements.

## Retriever integration contract (Person 1)

The agents depend on the `RegulationRetriever` protocol in
`src/food_label_compliance/retrieval.py`. Implement these two methods:

```python
search_regulations(query: str, source_type: str | None) -> list[dict]
lookup_clause(clause_id: str) -> dict | None
```

`source_type=None` searches all source types; claim review calls `"labeling"`
first and `"claims"` second. Every search result and successful clause lookup
must return these fields:

```text
source_id: str
regulation_name: str
clause_id: str
text: str
citation_id: str                  # canonical form: source_id:clause_id
citation_metadata: dict           # includes citation_id, source_id,
                                  # regulation_name, clause_id
source_type: str                  # for example "labeling" or "claims"
```

Clause IDs must be unique across the retriever because lookup takes only a
clause ID. The current typed contract also requires `supports_rule_ids: list[str]` and
`claim_keywords: list[str]` for deterministic rule/claim support checks; the
verifier checks citations against passages returned by `lookup_clause` and
stored by the Investigator. Citation metadata may include `evidence_scope`.
The default `MockRegulationRetriever` implements this contract using only the
fictional bundled corpus.

Inject another implementation without changing the agents:

```python
result = run_review(product_label, retriever=my_retriever)
```

The alternate retriever must supply its own source identity and citation
metadata. Injection does not make retrieved content authoritative; legal
conclusions still require verified regulatory evidence and appropriate human
review.

## Run tests

```powershell
.\venv\Scripts\python.exe -m unittest discover -s tests -v
```

## Project structure

```text
food-label-compliance/
├── .gitignore
├── README.md
├── pyproject.toml
├── requirements.txt
├── src/
│   └── food_label_compliance/
│       ├── __init__.py
│       ├── __main__.py
│       ├── agents.py
│       ├── retrieval.py
│       ├── regulation_tools.py
│       ├── data/
│       │   ├── mock_regulations.json
│       │   ├── mock_regulation_sources.json
│       │   ├── sample_label.json
│       │   └── sample_source_of_protein.json
│       └── workflow.py
└── tests/
    └── test_workflow.py
```
