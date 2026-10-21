
"""Retrieve relevant food-label regulations from the FAISS index."""

import re
from pathlib import Path

from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS

INDEX_PATH = Path("data/processed/index")
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"


def load_index():
    """Load the existing FAISS index."""
    embeddings = HuggingFaceEmbeddings(
        model_name=EMBEDDING_MODEL,
        encode_kwargs={"normalize_embeddings": True},
    )
    return FAISS.load_local(
        str(INDEX_PATH),
        embeddings,
        allow_dangerous_deserialization=True,
    )


def normalize_text(text):
    """Normalize whitespace, case, and hyphen variants."""
    text = str(text).casefold()
    text = re.sub(r"[-\u2010-\u2015]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def classify_query(query):
    """Classify a query by its most specific regulatory topic."""
    q = normalize_text(query)

    if any(term in q for term in (
        "health supplement",
        "nutraceutical",
        "dietary supplement",
    )):
        return "supplement"

    if any(term in q for term in (
        "sugar free", "sugars free", "sugar", "sugars",
        "0.5 g", "0.5g",
    )):
        return "sugar"

    if any(term in q for term in (
        "high protein", "source of protein", "protein claim",
    )):
        return "protein"

    if any(term in q for term in (
        "health claim", "health claims", "evidence",
        "substantiation",
    )):
        return "health"

    if any(term in q for term in (
        "nutrition information", "nutritional information",
        "energy", "nutrient declaration",
    )):
        return "nutrition"

    if "claim" in q and any(term in q for term in (
        "label", "labelling", "labeling", "wrapper", "package",
    )):
        return "claims"

    if "protein" in q:
        return "protein"

    if any(term in q for term in (
        "label", "labelling", "labeling", "wrapper",
        "packaged food", "declaration", "pre packaged",
        "pre-packaged", "retail food",
    )):
        return "labelling"

    return "general"


def regulation_id_for_source(source):
    """Map source filenames to regulation-family IDs."""
    name = Path(str(source)).stem.casefold().replace("_", " ")

    if any(term in name for term in (
        "health supplements compendium",
        "nutraceuticals",
        "nutraceutical",
        "health supplement",
    )):
        return "HS2016"

    if any(term in name for term in (
        "labelling", "labeling", "display",
    )):
        return "LD2020"

    if "advertising" in name or "claims" in name:
        return "AC2018"

    return "OTHER"


def extract_focused_excerpt(text, topic, max_chars=1200):
    """Return a focused excerpt for known claim-table sections."""
    text = re.sub(r"\s+", " ", str(text)).strip()
    if not text:
        return ""

    if topic == "sugar":
        start_pattern = r"\b10\s*[.]\s*sugars\b"
        end_pattern = r"\b11\s*[.]\s*protein\b"
    elif topic == "protein":
        start_pattern = r"\b11\s*[.]\s*protein\b"
        end_pattern = r"\b12\s*[.]\s*"
    else:
        return text[:max_chars]

    start_match = re.search(start_pattern, text, re.IGNORECASE)
    if not start_match:
        return text[:max_chars]

    remainder = text[start_match.end():]
    end_match = re.search(end_pattern, remainder, re.IGNORECASE)

    if end_match:
        excerpt = text[start_match.start():
                       start_match.end() + end_match.start()].strip()
    else:
        excerpt = text[start_match.start():].strip()

    return excerpt[:max_chars]


def keyword_score(text, source, topic):
    """Score topic wording and source-family relevance."""
    t = normalize_text(text)
    s = Path(str(source)).stem.casefold().replace("_", " ")

    keywords = {
        "protein": (
            "protein", "source", "high", "rich", "rda",
            "recommended dietary allowance", "100 g", "100g",
            "claim", "20%",
        ),
        "sugar": (
            "sugar", "sugars", "free", "0.5 g", "0.5g",
            "claim", "threshold",
        ),
        "health": (
            "health claim", "health", "evidence",
            "scientific", "substantiation",
        ),
        "nutrition": (
            "nutrition information", "nutritional information",
            "energy", "protein", "nutrient",
        ),
        "labelling": (
            "label", "labelling", "declaration",
            "name of food", "ingredients", "nutrition",
            "fssai logo", "licence number", "license number",
            "net quantity", "date marking", "batch number",
            "manufacturer", "allergen",
        ),
        "claims": (
            "claim", "claims", "advertising", "label",
            "wrapper", "nutrition claim", "schedule",
        ),
        "supplement": (
            "health supplement", "supplement",
            "specific labelling", "label declarations",
            "recommended usage", "warning",
        ),
        "general": ("food", "label", "regulation", "claim"),
    }

    score = sum(
        1 for term in keywords.get(topic, keywords["general"])
        if term in t
    )

    if topic in {"protein", "sugar", "health", "claims"}:
        if "advertising" in s or "claims" in s:
            score += 2

    if topic in {"labelling", "nutrition", "claims"}:
        if any(term in s for term in ("labelling", "labeling", "display")):
            score += 3

    if topic == "supplement":
        if any(term in s for term in (
            "nutraceutical", "supplement", "compendium",
        )):
            score += 2
        if "health supplement" in t:
            score += 2

    if topic == "protein":
        if any(term in t for term in (
            "protein source", "rich / high", "high protein",
            "high in protein", "rich in protein",
        )):
            score += 5
        if "recommended dietary allowance" in t or "rda" in t:
            score += 2
        if "sugars free" in t or "sugar free" in t:
            score -= 3

    elif topic == "sugar":
        if "sugars free" in t or "sugar free" in t:
            score += 10
        if "0.5 g" in t or "0.5g" in t:
            score += 4
        if "per 100 g" in t or "per 100g" in t:
            score += 2
        if "protein source" in t or "rich / high" in t:
            score -= 3

    elif topic == "labelling":
        if any(term in t for term in (
            "non retail container", "non retail containers",
            "non retail package", "non retail packages",
        )):
            score -= 8

        if any(term in t for term in (
            "name of the food", "list of ingredients",
            "nutrition information", "net quantity",
            "date marking", "fssai logo",
            "licence number", "license number",
            "name and address of the manufacturer",
            "allergen declaration",
        )):
            score += 3

    return score


def search_queries(query, topic):
    """Create complementary searches for each regulatory topic."""
    expansions = {
        "protein": [
            "Protein Source claim criteria and RDA requirements",
            "High protein claim conditions Source of protein RDA",
            "Protein claim threshold recommended dietary allowance",
            "Protein High Rich Schedule I nutrient content claim",
            "Food labelling nutrition declaration protein",
        ],
        "sugar": [
            "Sugars Free",
            "Sugars Free 0.5 g per 100 g Schedule I",
            "sugar free claim threshold 0.5 g per 100 g",
            "conditions for sugars free claim Schedule I",
            "sugars free claim conditions and requirements",
            "Food labelling nutrition declaration sugars",
        ],
        "health": [
            "health claim scientific evidence substantiation food",
            "advertising claims health claims conditions",
            "food labelling general mandatory declarations",
        ],
        "nutrition": [
            "food labelling nutritional information energy protein",
            "mandatory nutrition declaration prepackaged food",
        ],
        "claims": [
            "food advertising and claims appearing on food label wrapper",
            "nutrition claims conditions Schedule I Schedule II",
            "general mandatory food labelling requirements",
            "mandatory declarations prepackaged retail food",
            "name of food list of ingredients nutrition information",
        ],
        "labelling": [
            "mandatory declarations prepackaged retail food labelling",
            "name of food list of ingredients nutrition information",
            "net quantity date marking allergen declaration",
            "manufacturer details FSSAI logo licence number",
            "retail package mandatory labelling requirements",
        ],
        "supplement": [
            "health supplement specific labelling requirements",
            "health supplements regulations label declarations warnings",
            "general food labelling requirements prepackaged food",
            "food advertising and claims regulations health supplements",
        ],
        "general": [
            "mandatory food labelling declarations",
            "food advertising and claims regulations",
        ],
    }

    queries = [str(query)]
    queries.extend(expansions.get(topic, expansions["general"]))
    return list(dict.fromkeys(queries))


def is_relevant_claim_passage(text, topic):
    """Keep passages that directly support the requested claim."""
    t = normalize_text(text)

    if topic == "sugar":
        has_sugar_free_wording = (
            "sugars free" in t or "sugar free" in t
        )
        has_sugar_threshold = (
            "0.5 g of sugars" in t
            or "0.5g of sugars" in t
        )
        return has_sugar_free_wording and has_sugar_threshold

    if topic == "protein":
        has_protein_criteria = (
            "protein source" in t
            or "rich / high" in t
            or "rich high" in t
        )
        has_threshold = (
            "recommended dietary allowance" in t
            or "rda" in t
            or "20 per cent" in t
            or "20%" in t
        )
        return has_protein_criteria and has_threshold

    return True

def retrieve(vectorstore, query, top_k=5):
    """Retrieve, rank, and diversify relevant regulatory passages."""
    if top_k <= 0:
        return []

    topic = classify_query(query)
    candidates = {}

    for search_query in search_queries(query, topic):
        matches = vectorstore.similarity_search_with_score(
            search_query,
            k=50,
        )

        for document, distance in matches:
            metadata = document.metadata or {}
            source = metadata.get("source", "")
            page = metadata.get("page")
            content = document.page_content or ""

            key = (
                str(source),
                str(page),
                normalize_text(content),
            )

            score = (
                -float(distance)
                + 0.12 * keyword_score(content, source, topic)
            )

            result = {
                "source": source,
                "page": page,
                "text": extract_focused_excerpt(content, topic),
                "distance": float(distance),
                "score": score,
                "regulation_id": regulation_id_for_source(source),
                "citation": f"{source}, page {page}",
            }

            if key not in candidates or score > candidates[key]["score"]:
                candidates[key] = result

    ranked = sorted(
        candidates.values(),
        key=lambda item: item["score"],
        reverse=True,
    )

    # Prefer actual claim criteria over general background passages.
    
    if topic in {"sugar", "protein"}:
        relevant = [
            item for item in ranked
            if is_relevant_claim_passage(item["text"], topic)
        ]

    # For sugar-free searches, do not keep unrelated passages
    # if none of the candidates contain the required criteria.
        if topic == "sugar":
            ranked = relevant
        elif relevant:
            ranked = relevant

    # For retail labelling, deprioritize non-retail-container passages.
    if topic == "labelling":
        retail_relevant = [
            item for item in ranked
            if not any(term in normalize_text(item["text"]) for term in (
                "non retail container",
                "non retail containers",
                "non retail package",
                "non retail packages",
            ))
        ]
        if retail_relevant:
            ranked = retail_relevant

    # Keep only one passage per source/page.
    unique_pages = []
    seen_pages = set()

    for result in ranked:
        page_key = (str(result["source"]), str(result["page"]))
        if page_key in seen_pages:
            continue
        seen_pages.add(page_key)
        unique_pages.append(result)

    # For claim queries, retain the relevant regulatory families when found.
    if topic in {"claims", "protein"}:
        selected = []
        selected_keys = set()

        for family in ("AC2018", "LD2020"):
            match = next(
                (
                    item for item in unique_pages
                    if item["regulation_id"] == family
                ),
                None,
            )
            if match is not None and len(selected) < top_k:
                key = (str(match["source"]), str(match["page"]))
                if key not in selected_keys:
                    selected.append(match)
                    selected_keys.add(key)

        for item in unique_pages:
            key = (str(item["source"]), str(item["page"]))
            if key in selected_keys:
                continue

            selected.append(item)
            selected_keys.add(key)

            if len(selected) >= top_k:
                break

        selected.sort(key=lambda item: item["score"], reverse=True)
        return selected[:top_k]

    return unique_pages[:top_k]