from src.ingest import regulation_id_for
from src.retrieve import (
    classify_query,
    keyword_score,
    normalize_text,
    search_queries,
)
from src.evaluate import recall_at_k, reciprocal_rank


def test_regulation_id_mapping():
    assert regulation_id_for("FSSAI_Labelling_Display_2026.pdf") == "LD2020"
    assert regulation_id_for("Advertising_and_Claims_compendium.pdf") == "AC2018"
    assert regulation_id_for("other_food_rules.pdf") == "OTHER"


def test_query_classification_for_protein():
    assert classify_query(
        "Can this snack claim source of protein?"
    ) == "protein"


def test_query_classification_for_sugar_free():
    assert classify_query(
        "The label says sugar free. Which rule applies?"
    ) == "sugar"


def test_query_classification_for_labelling():
    assert classify_query(
        "What mandatory declarations must appear on a pre-packaged food label?"
    ) == "labelling"


def test_protein_search_queries_include_claim_criteria():
    queries = search_queries(
        "What conditions apply to a high protein claim?",
        "protein",
    )

    assert len(queries) >= 2
    assert any("RDA" in query for query in queries)
    assert any("Source" in query for query in queries)


def test_sugar_search_queries_include_threshold():
    queries = search_queries(
        "Which rule applies to a sugar free claim?",
        "sugar",
    )

    assert len(queries) >= 2
    assert any("0.5 g" in query for query in queries)


def test_keyword_score_prefers_relevant_protein_text():
    relevant = keyword_score(
        "Protein source and recommended dietary allowance RDA",
        "Original Advertising and Claims Regulations.pdf",
        "protein",
    )
    irrelevant = keyword_score(
        "Vegetable oils and fats",
        "Original Advertising and Claims Regulations.pdf",
        "protein",
    )

    assert relevant > irrelevant


def test_normalize_text():
    assert normalize_text("Sugar-Free   SNACK") == "sugar free snack"


def test_recall_at_k():
    assert recall_at_k(["LD2020", "AC2018"], {"AC2018"}, 2) == 1.0
    assert recall_at_k(["LD2020"], {"AC2018"}, 1) == 0.0


def test_reciprocal_rank():
    assert reciprocal_rank(
        ["LD2020", "AC2018"], {"AC2018"}, 5
    ) == 0.5

    assert reciprocal_rank(
        ["LD2020"], {"AC2018"}, 5
    ) == 0.0

def test_supplement_search_queries_include_specific_rules():
    queries = search_queries(
        "The food category is a health supplement. "
        "Is the general label rule enough?",
        "supplement",
    )

    assert len(queries) >= 3
    assert any("supplement" in query.lower() for query in queries)
    assert any("specific" in query.lower() for query in queries)