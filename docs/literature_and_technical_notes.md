# Literature and Technical Notes (Person 1)

## Official regulatory sources (primary sources)

1. Food Safety and Standards Authority of India (FSSAI), **Food Safety and Standards (Labelling and Display) Regulations, 2020**. Official amendment page: https://www.fssai.gov.in/food-law/regulations/amendments/labelling-display. The page lists amendments through 24 March 2026; use it to collect the latest text and amendments.
2. FSSAI, **Food Safety and Standards (Advertising and Claims) Regulations, 2018**. Official amendment page: https://www.fssai.gov.in/food-law/regulations/amendments/advertising-claims. The page lists amendments dated 9 October 2020, 30 August 2022, and 13 December 2022.
3. FSSAI, **Advertising and Claims Regulations compendium, 4 October 2022**: https://www.fssai.gov.in/upload/uploadfiles/files/Compendium_Advertising_Claims_Regulations_04_10_2022.pdf. Its Schedule I table gives protein “Source” and “Rich/High” thresholds. Verify against subsequent amendments before applying.
4. FSSAI, **Food Safety and Standards Regulations index**: https://www.fssai.gov.in/cms/food-safety-and-standards-regulations.php. Use this to identify additional rules relevant to product categories.

## Retrieval components

- **Sentence Transformers**: Reimers, N. and Gurevych, I. (2019). “Sentence-BERT: Sentence Embeddings using Siamese BERT-Networks.” *Proceedings of EMNLP-IJCNLP 2019*. https://aclanthology.org/D19-1410/ . Relevant because sentence embeddings can retrieve semantically related regulatory passages even when user wording differs from the regulation wording.
- **FAISS**: Johnson, J., Douze, M. and Jégou, H. (2017). “Billion-scale similarity search with GPUs.” https://arxiv.org/abs/1702.08734 . Relevant as a similarity-search index for vector retrieval.
- **Retrieval-Augmented Generation (RAG)**: Lewis, P. et al. (2020). “Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks.” NeurIPS 2020. https://arxiv.org/abs/2005.11401 . Relevant because answers are grounded in retrieved external evidence rather than model memory alone.
- **LangChain** documentation: https://python.langchain.com/docs/ . Used in this prototype for document objects, text splitting, embeddings and FAISS integration.

## Why a cross-regulation retrieval pipeline

A single semantic query can return only the most similar passages from one part of the corpus. The project’s hard case requires discovering that a label statement may be governed both by general labelling provisions and by a separate claim-specific instrument. The prototype therefore issues a bounded set of follow-up queries for claim-related inputs, retrieves candidate passages from the indexed corpus, deduplicates by source/page/content, and emits page-level evidence. The second agent/person can use this output for evidence verification and compliance routing.

## Evaluation plan

Use the eight starter cases in `tests/test_cases.jsonl` as an initial seed set. A domain reviewer must confirm the relevant regulation labels against the actual indexed current corpus. Report:

- Recall@5: proportion of all relevant regulation labels represented among top-k retrieved passages.
- MRR: reciprocal rank of the first relevant regulation label.
- Cross-regulation coverage: proportion of claim cases for which both `AC2018` and `LD2020` are retrieved in the top-k results.
- Citation support rate: proportion of generated findings for which each cited passage directly supports the statement (manual review).
- Escalation accuracy: whether missing evidence or uncertain applicability is routed to regulatory review rather than incorrectly labelled compliant.

Compare against a baseline that performs only one initial retrieval query. Use the same corpus, embedding model, top-k and labels. Do not report a numeric improvement until the experiment has actually been run on the reviewed current corpus.
