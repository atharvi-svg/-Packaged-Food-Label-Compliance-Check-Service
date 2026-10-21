
from src.compliance import (
    build_claim_reviews,
    check_label_text,
    format_passages,
)


def test_high_protein_claim_is_detected():
    findings = check_label_text(
        "Product Name: High-Protein Snack"
    )

    result = next(
        item for item in findings
        if item["check_id"] == "high_protein_claim"
    )

    assert result["detected"] is True


def test_sugar_free_claim_is_detected():
    findings = check_label_text(
        "Product Name: Sugar-Free Snack"
    )

    result = next(
        item for item in findings
        if item["check_id"] == "sugar_free_claim"
    )

    assert result["detected"] is True


def test_claim_reviews_retrieve_separately():
    findings = check_label_text(
        "High-Protein Sugar-Free Snack"
    )

    class FakeVectorStore:
        pass

    calls = []

    def fake_retrieve_references(
        vector_store, query, top_k
    ):
        calls.append(query)
        return [{
            "source": "test regulation.pdf",
            "page": 1,
            "excerpt": "Test regulatory passage",
            "citation": "test regulation.pdf, page 1",
        }]

    import src.compliance as compliance

    original = compliance.retrieve_references
    compliance.retrieve_references = fake_retrieve_references

    try:
        reviews = build_claim_reviews(
            findings=findings,
            vector_store=FakeVectorStore(),
            top_k=3,
        )
    finally:
        compliance.retrieve_references = original

    assert len(reviews) == 2
    assert len(calls) == 2
    assert all(
        review["detected"] is True
        for review in reviews
    )
    assert all(
        review["regulatory_references"]
        for review in reviews
    )
    assert calls[0] != calls[1]


def test_absent_claim_does_not_trigger_claim_retrieval():
    findings = check_label_text(
        "Product Name: Plain Roasted Snack"
    )

    class FakeVectorStore:
        pass

    reviews = build_claim_reviews(
        findings=findings,
        vector_store=FakeVectorStore(),
        top_k=3,
    )

    assert len(reviews) == 2
    assert all(
        review["detected"] is False
        for review in reviews
    )
    assert all(
        review["regulatory_references"] == []
        for review in reviews
    )


def test_format_passages_preserves_citation_and_page():
    passages = [{
        "citation": "Example Regulation.pdf, page 12",
        "source": "Example Regulation.pdf",
        "page": 12,
        "text": "Relevant regulatory passage.",
    }]

    references = format_passages(passages)

    assert len(references) == 1
    assert references[0]["citation"] == (
        "Example Regulation.pdf, page 12"
    )
    assert references[0]["source"] == "Example Regulation.pdf"
    assert references[0]["page"] == 12
    assert references[0]["excerpt"] == (
        "Relevant regulatory passage."
    )