# Evaluation log template

Populate this before the final demo. Do not invent measurements or leave expected source IDs ambiguous.

## Test set

Create `data/evaluation/questions.csv` with columns:

```csv
question_id,question,subject,question_type,expected_source_file,expected_page_or_function,relevant_chunk_ids,use_web_expected
```

Recommended mix for 12–15 queries: definitions, algorithm steps, dry runs, code-function questions, complexity questions, paraphrases, external applications/comparisons, and at least two unsupported questions.

## Retrieval comparison

Run the same query set through BM25-only, Qdrant dense-only, and hybrid RRF retrieval. Mark a hit when a manually labelled relevant source is present in the top k.

```text
Hit@3 = questions with a relevant source in top 3 / total questions
Hit@5 = questions with a relevant source in top 5 / total questions
```

| Retriever | Hit@3 | Hit@5 | Notes |
|---|---:|---:|---|
| BM25 | | | |
| Qdrant dense | | | |
| Hybrid RRF | | | |

## Answer quality

For each answer mark: `format_pass`, `citation_ids_valid`, `source_support` (supported/partial/unsupported), `complexity_correct`, `abstention_correct`, `manual_notes`.

A programmatic citation check only ensures the IDs exist in the evidence passed to the model. It does **not** establish that the evidence logically supports the adjacent claim. Manually inspect at least five answers.

## OCR pilot

| File/page | OCR runtime | Readable enough? | Formula/code errors | Action |
|---|---:|---|---|---|
| | | | | |

## Final summary

Report what was actually tested, not an estimated universal accuracy. Include missing pages, OCR failures, unsupported question behavior, known incorrect code in original sources, and which retrieval configuration performed best on the small test set.
