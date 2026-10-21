# Difficult Case: “Source of Protein” on a Packaged Solid Snack

## Case input

- Product category: packaged solid snack (category classification must be confirmed by the reviewer).
- Front-of-pack claim: **“Source of Protein”**.
- Illustrative nutrition declaration: protein = **6 g per 100 g**; product is a solid food.
- For arithmetic demonstration only, assume the applicable protein RDA basis is **50 g**. The actual RDA basis must be taken from the current applicable FSSAI text / cited schedule and verified before deciding compliance.
- Required evidence: the official current Advertising and Claims provision/Schedule I passage; applicable Labelling and Display passage for nutrition declaration; current nutrition analysis or other acceptable substantiation; current consolidated-version/amendment check.

## Calculation method

For a solid, calculate:

`% RDA per 100 g = (protein grams per 100 g / applicable protein RDA in grams) × 100`

Under the 50 g illustrative assumption:

`(6 / 50) × 100 = 12% RDA per 100 g`

The FSSAI Advertising and Claims compendium dated 4 October 2022 gives a “Source” protein criterion of at least 10% RDA per 100 g for solids; under the illustrative assumption, 12% clears that numeric threshold. This is **not a final compliance decision** because the RDA basis, current amendments, other claim conditions, nutrition evidence and product applicability must be verified.

## Expected retrieval behavior

1. Initial retrieval should return the applicable general labelling/nutrition-declaration passage.
2. The claim detector should trigger follow-up retrieval against Advertising and Claims Regulations and Schedule I protein criteria.
3. The output should cite source filename + page and quote the relevant passage. The exact clause/schedule reference must be verified against the original PDF.
4. The reasoning should display the inputs, formula, result, threshold and version caveat.
5. If current version, RDA basis or substantiation is missing, status should be `revise-and-recheck` or `regulatory-review`, not `clear-for-print`.

## Expected evidence checklist

- [ ] Current applicable claim definition/general conditions
- [ ] Current Schedule I protein “Source” threshold
- [ ] Labelling and Display nutrition declaration requirements
- [ ] Declared protein value and serving/100 g basis
- [ ] Applicable RDA basis and its source
- [ ] Product category and any additional applicable regulation
- [ ] Current amendment status and exact clause citations
