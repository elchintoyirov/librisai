"""
api.py — Libris AI FastAPI backend.

Run:
    uvicorn api:app --reload

Endpoints:
    GET  /books              — list all indexed books
    POST /books/upload       — upload and ingest a PDF
    DELETE /books/{book_id}  — delete a book and its index
    POST /chat               — single-turn chat (returns full answer)
    POST /chat/stream        — streaming chat via Server-Sent Events
"""

import json
import shutil
import tempfile
from pathlib import Path
from typing import Generator

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from libris.store import delete_book, get_book, ingest_book, list_books
from libris.retriever import load_retriever
from libris.llm import build_messages, stream_tokens, ask

# ── App ───────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="Libris AI",
    description="Chat with your PDF textbooks using local LLMs and hybrid RAG.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Retriever cache ───────────────────────────────────────────────────────────
# FAISS index load takes ~2s — cache by book_id so it only happens once.

@app.on_event("startup")
def startup():
    app.state.retrievers: dict = {}
    from libris.retriever import _get_embeddings
    _get_embeddings()


def _get_retriever(book_id: str):
    """Return cached retriever, loading from disk on first access."""
    if book_id not in app.state.retrievers:
        book = get_book(book_id)
        if book is None:
            raise HTTPException(status_code=404, detail=f"Book '{book_id}' not found.")
        app.state.retrievers[book_id] = load_retriever(book["index_path"])
    return app.state.retrievers[book_id]


# ── Schemas ───────────────────────────────────────────────────────────────────

class Message(BaseModel):
    role: str     # "user" or "assistant"
    content: str

class ChatRequest(BaseModel):
    book_id: str
    question: str
    history: list[Message] = []   # full conversation so far (stateless)

class ChatResponse(BaseModel):
    answer: str
    sources: list[int]            # chunk indices


# ── Book endpoints ────────────────────────────────────────────────────────────

@app.get("/books", summary="List all indexed books")
def get_books():
    return list_books()


@app.post("/books/upload", summary="Upload and ingest a PDF textbook")
def upload_book(file: UploadFile = File(...)):
    if not file.filename or not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted.")

    # Save the uploaded bytes to a temp file, then ingest from that path.
    with tempfile.NamedTemporaryFile(
        suffix=".pdf", delete=False,
        prefix=Path(file.filename).stem + "_"
    ) as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = Path(tmp.name)

    try:
        book = ingest_book(tmp_path)
    finally:
        tmp_path.unlink(missing_ok=True)

    return book


@app.delete("/books/{book_id}", summary="Delete a book and its FAISS index")
def remove_book(book_id: str):
    # Evict from cache if loaded
    app.state.retrievers.pop(book_id, None)

    if not delete_book(book_id):
        raise HTTPException(status_code=404, detail=f"Book '{book_id}' not found.")
    return {"deleted": book_id}


# ── Chat endpoints ────────────────────────────────────────────────────────────

@app.post("/chat", response_model=ChatResponse, summary="Single-turn chat (blocking)")
def chat(req: ChatRequest):
    """
    Returns the full answer once generation is complete.
    Use /chat/stream for a token-by-token response.
    """
    retriever = _get_retriever(req.book_id)
    history   = [m.model_dump() for m in req.history]

    source_docs, messages = build_messages(req.question, retriever, history)
    tokens = list(stream_tokens(messages))
    answer = "".join(tokens)

    sources = [
        doc.metadata.get("chunk_index", -1)
        for doc in source_docs
    ]
    return ChatResponse(answer=answer, sources=sources)


@app.post("/chat/stream", summary="Streaming chat via Server-Sent Events")
def chat_stream(req: ChatRequest):
    """
    Streams the answer token-by-token using Server-Sent Events (SSE).

    Event types:
      data: {"type": "token",  "content": "..."}
      data: {"type": "sources","content": [42, 47, ...]}
      data: {"type": "done"}

    Frontend example (JavaScript):
        const es = new EventSource('/chat/stream');
        es.onmessage = e => {
            const msg = JSON.parse(e.data);
            if (msg.type === 'token') appendText(msg.content);
        };
    """
    retriever = _get_retriever(req.book_id)
    history   = [m.model_dump() for m in req.history]
    source_docs, messages = build_messages(req.question, retriever, history)

    sources = [doc.metadata.get("chunk_index", -1) for doc in source_docs]

    def event_generator() -> Generator[str, None, None]:
        for token in stream_tokens(messages):
            payload = json.dumps({"type": "token", "content": token})
            yield f"data: {payload}\n\n"

        yield f"data: {json.dumps({'type': 'sources', 'content': sources})}\n\n"
        yield f"data: {json.dumps({'type': 'done'})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",   # disable nginx buffering if behind proxy
        },
    )


# ── Static files (UI) — must be mounted last ──────────────────────────────────
app.mount("/", StaticFiles(directory="static", html=True), name="static")
