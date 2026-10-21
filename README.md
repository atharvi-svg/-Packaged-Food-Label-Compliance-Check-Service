# Packaged Food Label Compliance Screening Prototype

## Overview

A Python-based prototype that screens packaged food label text for selected label declarations and nutrition claims. It retrieves relevant regulatory passages from a local FAISS index to support manual review.

## Features

* Detects nine categories of label text signals.
* Screens for high-protein and sugar-free claims.
* Retrieves regulatory passages from ingested PDF documents.
* Displays screening results in a Streamlit web interface.
* Exports the screening report as JSON.

## Technology Stack

* Python
* Streamlit
* FAISS
* Sentence Transformers
* LangChain
* Pytest

## Project Structure

* `src/ingest.py` — document ingestion
* `src/retrieve.py` — regulatory passage retrieval
* `src/compliance.py` — label screening and report generation
* `app.py` — Streamlit interface
* `tests/` — automated tests
* `data/raw/` — regulatory PDF documents
* `data/processed/` — processed documents and search index

## How to Run

Activate the project's virtual environment, then run:

```bash
python -m streamlit run app.py
```

Run the tests using:

```bash
PYTHONPATH=. python -m pytest -q
```

## Limitations

This is a screening prototype, not a legal compliance determination. Text detection does not establish that a declaration is correct or sufficient. Regulatory applicability, amendments, exceptions and retrieved references require manual verification against current official requirements.
