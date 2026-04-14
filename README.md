# Libris AI

A web-based RAG (Retrieval-Augmented Generation) application that lets students upload PDF textbooks and chat with them in Uzbek and English — powered by a local LLM via Ollama.

---

## What Was Built

### Architecture

```
PDF textbook
     │
     ▼
[ingest.py] ──── Docling / pdfminer extraction (best-of-two)
     │            ↓
     │           Text chunking (RecursiveCharacterTextSplitter)
     │            ↓
     │           HuggingFace multilingual embeddings
     │            ↓
     │           FAISS vector index saved to disk
     │
     ▼
[retriever.py] ── HybridRetriever
     │              BM25 (keyword exact match)  ─┐
     │              FAISS (semantic similarity) ─┴── Reciprocal Rank Fusion
     │
     ▼
[llm.py] ──────── Ollama local LLM (OpenAI-compatible API)
     │              Query preprocessing (strip question words)
     │              Language detection → Uzbek Latin / Cyrillic / English
     │              Token-by-token streaming via SSE
     │
     ▼
[api.py] ──────── FastAPI backend
     │              GET  /books              — list all indexed books
     │              POST /books/upload       — upload and ingest a PDF
     │              DELETE /books/{id}       — delete book and its index
     │              POST /chat/stream        — streaming chat (SSE)
     │
     ▼
[static/] ─────── Web UI
                   Book list + upload in sidebar
                   Streaming chat with source attribution
```

### Stack

| Component | Library / Tool |
|---|---|
| PDF extraction | Docling 2.87+ with pdfminer.six fallback |
| Chunking | LangChain `RecursiveCharacterTextSplitter` |
| Embeddings | `paraphrase-multilingual-MiniLM-L12-v2` |
| Vector store | FAISS (CPU, AVX2) |
| Keyword retrieval | `rank-bm25` via `langchain-community` |
| LLM | Ollama local (default: `qwen2.5:7b`) |
| Web backend | FastAPI + Uvicorn |
| File upload | `python-multipart` |
| Package manager | `uv` |
| Python | 3.12+ |

---

## Project Structure

```
librisai/
├── api.py                  # FastAPI app — all HTTP endpoints
├── libris/
│   ├── ingest.py           # PDF extraction, chunking, FAISS indexing
│   ├── retriever.py        # Hybrid BM25+FAISS retriever with RRF
│   ├── llm.py              # LLM client, prompt building, SSE streaming
│   └── store.py            # books.json metadata store (list/get/delete)
├── static/
│   ├── index.html          # Single-page web UI
│   ├── style.css           # Light theme styles
│   └── app.js              # Vanilla JS: book list, upload, streaming chat
├── data/                   # Created at runtime (gitignored)
│   ├── books/              # Uploaded PDF copies
│   ├── indexes/            # Per-book FAISS indexes
│   └── books.json          # Book metadata registry
└── pyproject.toml          # All dependencies (managed with uv)
```

---

## Setup

```bash
git clone https://github.com/elchintoyirov/librisai
cd librisai

uv sync

ollama pull qwen2.5:7b
```

Start Ollama (separate terminal):

```bash
ollama serve
```

Start the web server:

```bash
uvicorn api:app --reload
```

Then open [http://localhost:8000](http://localhost:8000) in your browser.

---

## Using the App

1. Click **+ Add Textbook** in the sidebar and select a PDF file.
2. Wait for ingestion to complete (a toast notification confirms it).
3. Click the book name to open a chat session.
4. Type your question and press **Send** — the answer streams back token by token.
5. Source chunks are shown below each AI response.
6. Click **↺ New chat** to clear history and start a fresh conversation.

---

## Future Improvements

### 1. Uzbek Morphological Analysis

Uzbek is agglutinative — "podsholigi", "podsholik", "podshoga" are all forms of the same root "podshoh" (king/kingdom). BM25 treats them as different tokens and misses matches.

**Improvement:** Integrate a stemmer or morphological analyzer specific to Uzbek. A custom suffix-stripping stemmer for the most common endings (`-ning`, `-ga`, `-da`, `-ligi`, `-lik`, `-lar`) would significantly improve BM25 recall without a full NLP pipeline.

---

### 2. Better Embedding Model for Uzbek

The current model (`paraphrase-multilingual-MiniLM-L12-v2`) covers 50+ languages but is not fine-tuned on Uzbek. It treats "bobil" (Babylon) and general "kingdom" concepts as similar, causing semantic drift.

**Improvement:** Fine-tune a sentence transformer on Uzbek textbook data, or use a model with stronger Central Asian language coverage. Even a small fine-tuning run on Uzbek Wikipedia passages would improve retrieval quality measurably.

---

### 3. Stronger Local LLM for Uzbek

`qwen2.5:7b` produces readable but grammatically imperfect Uzbek. It occasionally switches scripts or omits case suffixes.

**Improvement:** Use `qwen2.5:14b` or `qwen2.5:32b` if hardware allows — both produce noticeably better Uzbek. Alternatively, a model fine-tuned on Uzbek text (even a small 3B model fine-tuned specifically on Uzbek) would outperform a generic 7B model for this use case.

---

### 4. OCR for Scanned Textbooks

Many Uzbek school textbooks only exist as scanned PDFs (image pages, no text layer). The current pipeline fails silently on these — pdfminer returns empty text.

**Improvement:** Detect image-only pages and run OCR. Tesseract supports Uzbek Latin (`uzb`) and Uzbek Cyrillic (`uzb_cyrl`) — integrating it as a fallback when text extraction yields < 100 chars/page would handle scanned books.

```python
# Conceptual addition to ingest.py
if chars_per_page < 100:
    text = run_tesseract_ocr(pdf_path, lang="uzb")
```

---

### 5. Telegram Bot Interface

Most Uzbek students use Telegram daily. A bot interface would make the app accessible without any installation or browser.

**Improvement:** Add a Telegram bot using `aiogram`. Each user gets their own book selection and session. The bot can forward streamed responses chunk-by-chunk using message edit updates.

---

### 6. Per-Page Chunk Metadata

Currently chunks only store `source` (filename) and `chunk_index`. There is no page number attached to each chunk, so the app cannot tell the student which page to open for more context.

**Improvement:** Extract page boundaries during ingestion and tag each chunk with `page_number`. Show this in the source attribution: `[sources: page 47, page 51]` instead of `[sources: chunk 40, chunk 47]`.

---

### 7. Chunk Quality Filtering

pdfminer extracts everything including page numbers, headers, footers, table-of-contents lines, and image captions. These low-value chunks dilute retrieval.

**Improvement:** Filter chunks at ingestion time: discard any chunk under 100 characters, chunks that are purely numeric, or chunks matching known header/footer patterns. A simple regex pass would eliminate most noise.

---

### 8. Reranker After Retrieval

The current pipeline retrieves the top 6 chunks by RRF score and passes all of them to the LLM. Some of the 6 may be irrelevant even after fusion.

**Improvement:** Add a cross-encoder reranker (e.g., `cross-encoder/ms-marco-MiniLM-L-6-v2`) to score each retrieved chunk against the query and keep only the top 3. Cross-encoders are slower but much more accurate than bi-encoders for relevance scoring. This reduces noise in the LLM context and improves answer quality.

---

### 9. Evaluation Dataset

There is currently no way to measure whether a code change improved or degraded retrieval and answer quality. Changes are evaluated by manually testing a few questions.

**Improvement:** Build a small evaluation set of 50–100 question/answer pairs from the textbook, with known correct chunk indices. Use this to measure Recall@6 (did the right chunk appear in the top 6?) and answer correctness automatically after each change. This makes the system testable and prevents regressions.
