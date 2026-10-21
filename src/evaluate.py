
"""Evaluate source-level, provision-level, and keyword retrieval quality."""

import json
import re
from pathlib import Path

from src.retrieve import load_index, retrieve

TEST_CASES_PATH = Path("tests/test_cases.jsonl")
TOP_K = 5


def load_test_cases(path):
    """Read one JSON test case per line."""
    cases = []

    with path.open("r", encoding="utf-8") as file:
        for line_number, line in enumerate(file, start=1):
            line = line.strip()

            if not line or line.startswith("#"):
                continue

            try:
                cases.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"Invalid JSON on line {line_number} "
                    f"of {path}: {exc}"
                ) from exc

    return cases


def normalize_source(value):
    """Map regulation IDs or source PDF filenames to family IDs."""
    name = Path(str(value)).stem.lower().replace("_", " ").strip()

    # Accept IDs that are already normalized.
    if name in {"ld2020", "ac2018","hs2016", "other"}:
        return name.upper()

    if (
        name == "original labelling regulations"
        or name.startswith("labelling amendment")
        or name == "original labeling regulations"
        or name.startswith("labeling amendment")
    ):
        return "LD2020"

    if (
        name == "original advertising and claims regulations"
        or name.startswith("advertising and claims amendment")
    ):
        return "AC2018"
    if (
        "health supplements compendium" in name
        or "nutraceuticals" in name
        or "health supplement" in name
    ):
        return "HS2016"   
    # Matches regulation_id_for() in src/ingest.py.
    return "OTHER"


def get_relevant_ids(case):
    """Read expected regulation-family IDs or source filenames."""
    possible_keys = (
        "relevant_regulation_ids",
        "relevant_sources",
        "relevant_source_ids",
        "relevant_ids",
        "relevant_documents",
    )

    for key in possible_keys:
        value = case.get(key)

        if value:
            if isinstance(value, str):
                value = [value]

            return {
                normalize_source(item)
                for item in value
                if str(item).strip()
            }

    return set()


def recall_at_k(retrieved_ids, relevant_ids, k):
    """Calculate source-family Recall@k."""
    if not relevant_ids:
        return None

    found = set(retrieved_ids[:k]) & relevant_ids
    return len(found) / len(relevant_ids)


def reciprocal_rank(retrieved_ids, relevant_ids, k):
    """Return reciprocal rank of the first relevant source."""
    if not relevant_ids:
        return None

    for rank, source_id in enumerate(retrieved_ids[:k], start=1):
        if source_id in relevant_ids:
            return 1.0 / rank

    return 0.0


def keyword_matches(text, keywords):
    """Match expected keywords, tolerating spaces in numeric units."""
    text = text.casefold()

    text = re.sub(
        r"(?<=\d)\s+(?=(?:g|mg|kg|ml|l|kcal)\b)",
        "",
        text,
    )

    matched = []
    missing = []

    for keyword in keywords:
        keyword = str(keyword).strip()

        if not keyword:
            continue

        normalized_keyword = re.sub(
            r"(?<=\d)\s+(?=(?:g|mg|kg|ml|l|kcal)\b)",
            "",
            keyword.casefold(),
        )

        pattern = (
            r"(?<!\w)"
            + re.escape(normalized_keyword)
            + r"(?!\w)"
        )

        if re.search(pattern, text):
            matched.append(keyword)
        else:
            missing.append(keyword)

    return matched, missing


def normalize_filename(value):
    """Normalize a PDF filename for provision matching."""
    return Path(str(value)).name.casefold().strip()


def normalize_page(value):
    """Normalize page numbers for comparison."""
    if value is None:
        return None

    value = str(value).strip()

    if not value:
        return None

    return value


def evaluate_provisions(results, expected_provisions, k):
    """Match expected source/page pairs against the top-k passages."""
    if not expected_provisions:
        return None, [], []

    top_results = results[:k]
    matched = []
    missing = []

    for provision in expected_provisions:
        expected_source = normalize_filename(
            provision.get("source", "")
        )
        expected_page = normalize_page(provision.get("page"))

        found = False

        if expected_source and expected_page is not None:
            for result in top_results:
                result_source = normalize_filename(
                    result.get("source", "")
                )
                result_page = normalize_page(result.get("page"))

                if (
                    result_source == expected_source
                    and result_page == expected_page
                ):
                    found = True
                    break

        if found:
            matched.append(provision)
        else:
            missing.append(provision)

    recall = len(matched) / len(expected_provisions)
    return recall, matched, missing


def main():
    if not TEST_CASES_PATH.exists():
        raise FileNotFoundError(
            f"Test cases file not found: {TEST_CASES_PATH}"
        )

    cases = load_test_cases(TEST_CASES_PATH)

    if not cases:
        raise ValueError(
            f"No test cases found in {TEST_CASES_PATH}"
        )

    vector_store = load_index()

    recalls = []
    reciprocal_ranks = []
    keyword_coverages = []
    provision_recalls = []

    skipped = 0
    details = []

    for index, case in enumerate(cases, start=1):
        case_id = case.get(
            "case_id", case.get("id", f"TC{index:02d}")
        )

        query = (
            case.get("query")
            or case.get("question")
            or case.get("user_query")
            or ""
        ).strip()

        if not query:
            print(
                f"Skipping {case_id}: "
                "no query/question field."
            )
            skipped += 1
            continue

        results = retrieve(
            vectorstore=vector_store,
            query=query,
            top_k=TOP_K,
        )

        # Normalize and deduplicate retrieved source families.
        retrieved_ids = list(
            dict.fromkeys(
                normalize_source(result.get("source", ""))
                for result in results
            )
        )

        relevant_ids = get_relevant_ids(case)

        expected_keywords = case.get("expected_keywords", [])

        if isinstance(expected_keywords, str):
            expected_keywords = [expected_keywords]

        combined_text = "\n".join(
            str(result.get("text", ""))
            for result in results
        )

        matched_keywords, missing_keywords = keyword_matches(
            combined_text,
            expected_keywords,
        )

        if expected_keywords:
            keyword_coverage = (
                len(matched_keywords) / len(expected_keywords)
            )
            keyword_coverages.append(keyword_coverage)
        else:
            keyword_coverage = None

        detail = {
            "case_id": case_id,
            "query": query,
            "expected_keywords": expected_keywords,
            "matched_keywords": matched_keywords,
            "missing_keywords": missing_keywords,
            "keyword_coverage": (
                round(keyword_coverage, 4)
                if keyword_coverage is not None
                else None
            ),
            "retrieved_sources": [
                result.get("source", "")
                for result in results
            ],
            "retrieved_pages": [
                result.get("page")
                for result in results
            ],
        }

        # Source-family Recall@k and MRR.
        if relevant_ids:
            recall = recall_at_k(
                retrieved_ids, relevant_ids, TOP_K
            )
            rr = reciprocal_rank(
                retrieved_ids, relevant_ids, TOP_K
            )

            recalls.append(recall)
            reciprocal_ranks.append(rr)

            detail.update({
                "scored": True,
                "relevant_regulation_ids": sorted(relevant_ids),
                "retrieved_regulation_ids": retrieved_ids,
                "recall_at_k": round(recall, 4),
                "reciprocal_rank": round(rr, 4),
            })
        else:
            print(
                f"Note: {case_id} has no recognized "
                "source relevance labels."
            )
            skipped += 1
            detail["scored"] = False

        # Provision-level Recall@k.
        expected_provisions = case.get("expected_provisions", [])

        if isinstance(expected_provisions, dict):
            expected_provisions = [expected_provisions]

        (
            provision_recall,
            matched_provisions,
            missing_provisions,
        ) = evaluate_provisions(
            results,
            expected_provisions,
            TOP_K,
        )

        if provision_recall is not None:
            provision_recalls.append(provision_recall)

        detail.update({
            "expected_provisions": expected_provisions,
            "matched_provisions": matched_provisions,
            "missing_provisions": missing_provisions,
            "provision_recall_at_k": (
                round(provision_recall, 4)
                if provision_recall is not None
                else None
            ),
        })

        details.append(detail)

    summary = {
        "test_cases_loaded": len(cases),
        "cases_scored": len(recalls),
        "cases_skipped_or_unscored": skipped,
        "k": TOP_K,
        "mean_recall_at_k": (
            round(sum(recalls) / len(recalls), 4)
            if recalls else None
        ),
        "mrr": (
            round(
                sum(reciprocal_ranks) / len(reciprocal_ranks),
                4,
            )
            if reciprocal_ranks else None
        ),
        "mean_keyword_coverage": (
            round(
                sum(keyword_coverages) / len(keyword_coverages),
                4,
            )
            if keyword_coverages else None
        ),
        "provision_cases_scored": len(provision_recalls),
        "mean_provision_recall_at_k": (
            round(
                sum(provision_recalls) / len(provision_recalls),
                4,
            )
            if provision_recalls else None
        ),
        "metric_note": (
            "Recall@k and MRR measure source-family retrieval. "
            "Provision Recall@k checks expected source/page pairs "
            "among the top-k passages. Keyword coverage measures "
            "literal matches in retrieved text. These metrics "
            "do not independently establish legal correctness."
        ),
        "details": details,
    }

    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()