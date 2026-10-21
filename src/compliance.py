
"""Rule-based packaged food label screening prototype.

Checks for text signals and retrieves relevant regulatory passages.
This tool does not establish legal compliance.
"""

import argparse
import json
import re

from src.retrieve import load_index, retrieve


LABEL_CHECKS = {
    "name_of_food": {
        "label": "Name of food",
        "patterns": [
            r"\bname\s+of\s+(the\s+)?food\b",
            r"\bproduct\s+name\b",
        ],
    },
    "ingredients": {
        "label": "Ingredients list",
        "patterns": [
            r"\bingredients\b",
            r"\blist\s+of\s+ingredients\b",
        ],
    },
    "nutrition_information": {
        "label": "Nutrition information",
        "patterns": [
            r"\bnutrition(al)?\s+information\b",
            r"\bnutrition\s+facts\b",
        ],
    },
    "net_quantity": {
        "label": "Net quantity",
        "patterns": [
            r"\bnet\s+(quantity|weight|volume|contents)\b",
        ],
    },
    "date_marking": {
        "label": "Date marking",
        "patterns": [
            r"\b(best\s+before|use\s+by|expiry|expires|expiry\s+date)\b",
        ],
    },
    "manufacturer_details": {
        "label": "Manufacturer or packer details",
        "patterns": [
            r"\bmanufactured\s+by\b",
            r"\bmarketed\s+by\b",
            r"\bpacked\s+by\b",
            r"\bmanufacturer\b",
        ],
    },
    "fssai_license": {
        "label": "FSSAI licence identifier",
        "patterns": [
            r"\bfssai\b",
            r"\blicen[cs]e\s*(?:no\.?|number)\b",
        ],
    },
    "high_protein_claim": {
        "label": "High-protein claim",
        "patterns": [
            r"\bhigh[- ]protein\b",
            r"\bhigh\s+in\s+protein\b",
            r"\bprotein[- ]rich\b",
            r"\brich\s+in\s+protein\b",
        ],
    },
    "sugar_free_claim": {
        "label": "Sugar-free claim",
        "patterns": [
            r"\bsugar[- ]free\b",
            r"\bfree\s+from\s+sugars?\b",
            r"\bno\s+sugar\b",
            r"\bzero\s+sugars?\b",
        ],
    },
}



GENERAL_LABEL_QUERY = (
    "Food Safety and Standards Labelling and Display Regulations "
    "pre-packaged retail food mandatory label declarations "
    "name of food list of ingredients nutrition information "
    "allergen declaration net quantity date marking "
    "manufacturer or packer details FSSAI logo licence number"
)

CLAIM_QUERIES = {
    "high_protein_claim": (
        "Food Advertising and Claims Regulations, protein nutrient "
        "content claim, source of protein, rich or high protein, "
        "recommended dietary allowance RDA criteria and conditions"
    ),
    "sugar_free_claim": (
        "Food Advertising and Claims Regulations, sugars free claim, "
        "maximum permitted sugars per 100 g solid food or per 100 ml "
        "liquid food, applicable conditions and amendments"
    ),
}


def normalize(text):
    """Normalize whitespace and case for text matching."""
    return re.sub(r"\s+", " ", text).casefold()


def check_label_text(label_text):
    """Detect phrases in label text without judging legal compliance."""
    normalized = normalize(label_text)
    findings = []

    for check_id, rule in LABEL_CHECKS.items():
        detected = any(
            re.search(pattern, normalized)
            for pattern in rule["patterns"]
        )

        findings.append({
            "check_id": check_id,
            "item": rule["label"],
            "status": (
                "Text detected"
                if detected
                else "Not detected - review required"
            ),
            "detected": detected,
            "note": (
                "Text presence does not establish that the declaration "
                "or claim is legally correct or sufficient."
                if detected
                else
                "Text was not detected. Confirm applicability and "
                "inspect the original package before concluding that "
                "the declaration or claim is missing."
            ),
        })

    return findings


def format_passages(passages):
    """Convert retrieved documents into JSON-friendly references."""
    references = []

    for item in passages:
        references.append({
            "citation": item.get("citation"),
            "source": item.get("source"),
            "page": item.get("page"),
            "excerpt": item.get("text", "")[:1200],
        })

    return references


def retrieve_references(vector_store, query, top_k):
    """Retrieve passages for one specific query."""
    passages = retrieve(
        vectorstore=vector_store,
        query=query,
        top_k=top_k,
    )
    return format_passages(passages)


def build_claim_reviews(findings, vector_store, top_k):
    """Retrieve evidence separately for each detected nutrition claim."""
    claim_reviews = []

    for check_id, query in CLAIM_QUERIES.items():
        finding = next(
            item for item in findings
            if item["check_id"] == check_id
        )

        if finding["detected"]:
            references = retrieve_references(
                vector_store=vector_store,
                query=query,
                top_k=top_k,
            )

            status = "Detected - criteria review required"
            note = (
                "Review the retrieved provisions and verify the current "
                "applicable regulations, product category, required "
                "nutrient values and conditions before deciding whether "
                "the claim is permitted."
            )
        else:
            references = []
            status = "Claim not detected"
            note = (
                "No claim-specific retrieval was run because the claim "
                "wording was not detected in the supplied text. This "
                "does not establish that the claim is absent from the "
                "original package."
            )

        claim_reviews.append({
            "check_id": check_id,
            "claim": finding["item"],
            "status": status,
            "detected": finding["detected"],
            "retrieval_query": query if finding["detected"] else None,
            "review_note": note,
            "regulatory_references": references,
        })

    return claim_reviews


def main():
    parser = argparse.ArgumentParser(
        description="Packaged food label screening prototype."
    )

    parser.add_argument(
        "--label",
        required=True,
        help="Text transcribed or extracted from a food label.",
    )

    parser.add_argument(
        "--top-k",
        type=int,
        default=3,
        help="Number of regulatory passages per query (default: 3).",
    )

    args = parser.parse_args()

    if not args.label.strip():
        parser.error("--label must not be empty")

    if args.top_k < 1:
        parser.error("--top-k must be at least 1")

    # Run the original nine text-presence checks.
    findings = check_label_text(args.label)

    # Load the existing index; do not rebuild it.
    vector_store = load_index()

    # Retrieve general labelling requirements separately.
    general_references = retrieve_references(
        vector_store=vector_store,
        query=GENERAL_LABEL_QUERY,
        top_k=args.top_k,
    )

    # Retrieve claim-specific evidence independently.
    claim_reviews = build_claim_reviews(
        findings=findings,
        vector_store=vector_store,
        top_k=args.top_k,
    )

    report = {
        "tool": "Packaged Food Label Compliance Screening Prototype",
        "overall_status": "Manual review required",
        "disclaimer": (
            "This prototype detects text patterns and retrieves "
            "regulatory passages. It does not establish legal "
            "compliance or verify that every applicable requirement "
            "has been met. Applicability depends on the product, "
            "label format, relevant regulations, exceptions and "
            "amendments. Verify current official requirements and "
            "inspect the original package before making a decision."
        ),
        "summary": {
            "text_checks_total": len(findings),
            "text_checks_detected": sum(
                1 for item in findings if item["detected"]
            ),
            "text_checks_not_detected": sum(
                1 for item in findings if not item["detected"]
            ),
            "claims_detected": sum(
                1 for item in claim_reviews if item["detected"]
            ),
        },
        "findings": findings,
        "general_labelling_references": general_references,
        "claim_reviews": claim_reviews,
    }

    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()