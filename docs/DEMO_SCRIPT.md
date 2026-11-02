# 3-Minute Demo Script — Syllabus-Aware DS/AoA NLP Assistant

## Overview
This walkthrough presents the end-to-end capabilities of the **Syllabus-Aware DS/AoA Course QA Assistant** in 3 minutes, covering typed lecture notes, C code implementations, web-augmented retrieval, and out-of-corpus abstention.

---

## Pre-Flight Check (Before Presentation)
1. Ensure virtual environment is active:
   ```bash
   source .venv/bin/activate
   ```
2. Verify all tests pass:
   ```bash
   pytest -q
   # Expected: 106 passed
   ```
3. Launch the assistant:
   ```bash
   python run.py
   # Or: python -m course_qa.app
   ```
4. Open your browser at **`http://localhost:7860`**.

---

## 3-Minute Presentation Walkthrough

### Part 1: Architecture & Data Ingestion (0:00 – 0:45)
- **What to say:**
  > "Our project is a syllabus-aware question answering assistant designed specifically for Data Structures and Analysis of Algorithms. We ingested 86 course files comprising 575 canonical chunks: typed lecture notes, 41 C lab implementations, and syllabus documents, while indexing 281 handwritten pages for OCR. We use a hybrid retrieval pipeline combining dense vector embeddings in Qdrant with Okapi BM25 lexical search, fused using Reciprocal Rank Fusion."
- **What to show in the UI:**
  - Highlight the clean interface, the **Subject Filter** (`Any`, `DS`, `AOA`), the **Answer Style** (`exam`, `concise`), and the **Web Augmentation** toggle.

---

### Part 2: Typed Notes & Page Image Citation (0:45 – 1:30)
- **Action:**
  - Click the benchmark sample button: **"Fractional Knapsack (AOA)"**
    *(or type: `Define the fractional knapsack problem and explain its greedy choice criterion.`)*
  - Keep Subject: **AOA**, Web Augmentation: **OFF**.
  - Click **Submit Question**.
- **What to say:**
  > "Notice how the model grounds its answer strictly in the course materials. It provides structured exam-style sections with explicit `[S1]`, `[S2]` citations. When we switch to the **Sources** tab, every citation links back to the exact PDF (`Fractional_Knapsack.pdf`) and page number. In the **Page Scans** tab, the original slide/page image is rendered directly for the student to cross-check."
- **What to show:**
  - The generated answer with inline source tags `[S1]`, `[S2]`.
  - The **Sources** table showing `Fractional_Knapsack.pdf` and page numbers.
  - The **Page Scans** gallery showing the rendered slide image.

---

### Part 3: C Code & Function-Level Granularity (1:30 – 2:15)
- **Action:**
  - Click benchmark sample button: **"Dijkstra Relaxation (Code)"** or **"Reverse Linked List (DS)"**.
    *(Query: `Explain how reverse() reverses the linked list using three pointers in LinkedList6p.c.`)*
  - Subject: **DS**, Web Augmentation: **OFF**.
  - Click **Submit Question**.
- **What to say:**
  > "Rather than treating source code as generic text, our ingestion pipeline parses C code into function-level chunks. Here, the system retrieves the exact `reverse()` function from `LinkedList6p.c` with its pointer invariants, rather than pulling irrelevant boilerplate from `main()` or other utilities."
- **What to show:**
  - The **Sources** table displaying `function_name: reverse` and source file `ds_codes/LinkedList6p.c`.

---

### Part 4: Web Search Permission Gate & Fallback (2:15 – 2:45)
- **Action:**
  - Click benchmark button: **"Dijkstra Applications (Web)"**.
    *(Query: `Give real-world practical applications of Dijkstra algorithm in computer networks.`)*
  - Check the box: **Enable Web Search Augmentation**.
  - Click **Submit Question**.
- **What to say:**
  > "Our architecture enforces a strict notes-first permission gate. When web search is disabled, zero external network calls are made. When enabled for queries requiring external context, the system queries allowlisted educational domains (such as NPTEL, GeeksforGeeks, and GitHub). Web evidence is clearly demarcated from course notes with separate source labels and URLs."
- **What to show:**
  - The telemetry indicating `Web Search: True` and web citations with domain URLs.

---

### Part 5: Out-of-Corpus Abstention & Safety (2:45 – 3:00)
- **Action:**
  - Click benchmark button: **"Out-of-Corpus Query (Abstain)"**.
    *(Query: `What exact grading rubric did my instructor privately use for this class?`)*
  - Subject: **Any**, Web Augmentation: **OFF**.
  - Click **Submit Question**.
- **What to say:**
  > "A core vulnerability of naive RAG is hallucinating answers when evidence is absent. Our system evaluates retrieval confidence: if no course evidence supports the question, the system refuses to fabricate claims and triggers an explicit abstention warning."
- **What to show:**
  - The abstention status tag and warning banner.

---

## Key Metrics Summary for Presentation Slides

```text
Corpus Size                     : 575 canonical chunks (86 files)
Hybrid Retrieval (Dense + BM25) : Reciprocal Rank Fusion (k=60)
Retrieval Accuracy              : Hit@5 = 78.6%
Citation Validity Rate          : 100.0% (strict regex extraction & pruning)
Abstention Precision           : 93.3%
Test Suite Coverage             : 106 unit & integration tests passing (100%)
Startup Time                    : < 1.5s
```
