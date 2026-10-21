# Retrieval Accuracy Test Plan

## Objective
Measure whether retrieval finds the correct regulatory family for common label questions and whether cross-regulation queries improve coverage on claims.

## Dataset
Start with `tests/test_cases.jsonl`. It is a seed set, not a validated benchmark. Add at least 30–50 cases reviewed by a food regulatory subject-matter expert before making strong performance claims. Include ordinary label fields, nutrient claims, health claims, product-category exceptions, ambiguous wording, missing nutritional values and amendment/version conflicts.

## Metrics
- **Recall@k**: relevant regulation IDs appearing in the first k retrieved candidates divided by all relevant IDs.
- **MRR**: mean reciprocal rank of the first relevant candidate.
- **Cross-regulation coverage**: claim test cases retrieving both the claims and labelling instruments in top k.
- **Citation support rate**: manually scored proportion of cited snippets that support the associated finding.
- **Abstention/escalation accuracy**: whether missing data, unresolved amendment status or ambiguous product classification correctly leads to review.

## Experiment protocol
1. Download and version-control the latest official PDFs and amendments.
2. Have a reviewer annotate relevant regulation IDs and, separately, exact clauses/pages.
3. Run baseline single-query retrieval and the follow-up query pipeline using identical top-k.
4. Calculate metrics with `src/evaluate.py`; manually audit at least 20 outputs.
5. Record embedding model, chunk size/overlap, corpus checksums, date and configuration.
6. Report failures and examples, not just averages. Do not call retrieval recall “legal accuracy.”

## Acceptance criteria (proposed, not achieved)
- Recall@5 >= 0.90 on reviewed test cases.
- 100% of claim cases missing essential nutrition data are routed to revise/recheck or regulatory review.
- No compliance decision without supporting passages and a reviewed applicable version.
- Every output includes source file and page; exact clause citations must be manually verified.
