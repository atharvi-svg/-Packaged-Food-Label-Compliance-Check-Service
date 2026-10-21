# Regulatory Corpus and Clause Identification Notes

## Research scope

The initial corpus focuses on two FSSAI instruments identified in the project brief:

1. **Food Safety and Standards (Labelling and Display) Regulations, 2020** — general packaged-food labelling and display requirements.
2. **Food Safety and Standards (Advertising and Claims) Regulations, 2018** — requirements for claims made on food labels and in advertising, including nutrient-content claims.

This pair is useful for the difficult case because a label can meet general presentation requirements while a specific claim on that label still needs to satisfy claim-specific conditions. Depending on product category and claim wording, additional rules may apply (for example, product standards, fortified foods, organic foods, or foods for special dietary uses). The index should therefore be extensible rather than hard-coded to only two regulations.

## Official source register

See `regulatory_source_register.csv`. The FSSAI amendment page for Labelling and Display lists an amendment dated **24 March 2026**. The consolidated PDF dated 3 April 2025 is not sufficient by itself for a current 2026 assessment. The Advertising and Claims amendment page lists amendments dated 9 October 2020, 30 August 2022, and 13 December 2022. Check the official FSSAI index and Gazette notifications for any subsequent instrument before final legal use.

## Starter clause map (to verify against downloaded official text)

| Question | Primary source to retrieve | Cross-check |
|---|---|---|
| Which general declarations are required on a pre-packaged food? | Labelling and Display Regulations, applicable general labelling provisions | Product-category-specific rules and later amendments |
| Is “source of protein” permitted? | Advertising and Claims Regulations, claim definitions/general conditions and Schedule I protein threshold | Labelling and Display requirements for nutrition declaration and claim presentation |
| What nutrient quantity should support a nutrition/health claim? | Advertising and Claims Regulations, applicable general conditions for claims | Nutrition declaration in the label and the product's substantiation records |
| Does a specific product type have extra requirements? | Relevant product-specific FSSAI regulation/standard | Labelling and Display plus Advertising and Claims |

The table intentionally avoids asserting clause numbers where they have not yet been verified against the exact consolidated and amended text downloaded for this project.

## “Source of protein” test case

The FSSAI Advertising and Claims compendium dated 4 October 2022 includes a Schedule I table for protein claims. The table states “Source” criteria of at least 10% of RDA per 100 g for solids, 5% of RDA per 100 ml for liquids, or 5% of RDA per 100 kcal; “Rich/High” criteria are at least 20% of RDA per 100 g for solids, 10% of RDA per 100 ml for liquids, or 10% of RDA per 100 kcal. Treat these as **starter extraction targets**, not as final legal advice: confirm the applicable current version, RDA basis, product form, relevant amendments and all other conditions before using a result.

A robust checker must not infer compliance from the phrase alone. It needs the food form (solid/liquid), declared protein per 100 g/100 ml and/or per 100 kcal, the applicable RDA basis and supporting evidence. If any of those are missing, the correct system state is “revise and recheck” or “regulatory review,” not “compliant.”

## Document-control requirements

For every PDF stored under `data/raw/`, record:

- exact title and regulation identifier;
- issuing authority and official URL;
- publication/consolidation date and amendment dates included;
- download date;
- SHA-256 checksum;
- effective date / applicability notes;
- whether superseded or awaiting legal review.

Do not merge amendments into a “current” text without recording the source and effective date. If amendment text conflicts with a prior consolidated copy, preserve both and require a reviewed consolidation.

## Citation format

Every retrieved passage should display its source filename, PDF page number and a short quoted excerpt. A clause number should only be shown if extracted and checked against the original official document. The prototype cites filename/page and retrieved text; clause-level citations are a human-reviewed extension, not something to fabricate from semantic similarity.
