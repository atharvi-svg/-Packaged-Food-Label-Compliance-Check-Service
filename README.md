# Packaged Food Label Compliance Check Service

## Overview

This repository combines a packaged food label screening prototype with a deterministic, evidence-verification workflow. It is intended to support preliminary screening and manual regulatory review, not to certify legal compliance.

The repository contains two components:

### Person 1 — Label Screening Prototype

A Python-based application that screens packaged food label text for selected declarations and nutrition claims.

Features:
- Detects nine categories of label text signals.
- Screens for high-protein and sugar-free claims.
- Retrieves relevant regulatory passages from a local FAISS index.
- Provides a Streamlit web interface.
- Exports screening reports as JSON.

Key files:
- `app.py` — Streamlit interface
- `src/ingest.py` — document ingestion
- `src/retrieve.py` — regulatory passage retrieval
- `src/compliance.py` — label screening and report generation
- `src/evaluate.py` — evaluation utilities
- `tests/test_compliance.py` and `tests/test_retrieval.py` — prototype tests

### Person 2 — Evidence Verification Workflow

A deterministic LangGraph workflow that uses mock regulatory sources to demonstrate claim investigation, citation verification, and escalation for human review.

Features:
- A Compliance Investigator searches mock regulatory sources.
- An Evidence Verifier checks citations against retrieved passages.
- A bounded retry is attempted when evidence is missing.
- Unverified findings and insufficient evidence are escalated for regulatory review.
- Structured JSON audit reports record searches, citations, verification explanations, and review outcomes.

Key files:
- `src/food_label_compliance/agents.py` — workflow agents
- `src/food_label_compliance/retrieval.py` — retriever interface and mock implementation
- `src/food_label_compliance/regulation_tools.py` — regulatory retrieval tools
- `src/food_label_compliance/workflow.py` — review workflow
- `src/food_label_compliance/__main__.py` — command-line entry point
- `tests/test_workflow.py` — workflow tests

The Person 2 workflow uses fictional mock regulations for development and testing. These mock passages are not FSSAI requirements and cannot establish legal compliance.

## Technology Stack

- Python
- Streamlit