"""
ingest.py — PDF extraction, chunking, embedding, and FAISS indexing pipeline.

Usage:
    from libris.ingest import ingest_book
    book = ingest_book("data/books/physics.pdf")
"""

import json
import uuid
import logging
from pathlib import Path
from datetime import datetime

from docling.document_converter import DocumentConverter

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS

# ── Logging ───────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  [%(levelname)s]  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

# ── Paths ─────────────────────────────────────────────────────────────────────

ROOT        = Path(__file__).resolve().parent.parent
INDEXES_DIR = ROOT / "data" / "indexes"
STORE_FILE  = ROOT / "data" / "books.json"

INDEXES_DIR.mkdir(parents=True, exist_ok=True)
STORE_FILE.parent.mkdir(parents=True, exist_ok=True)

# ── Chunking config ───────────────────────────────────────────────────────────

CHUNK_SIZE    = 800
CHUNK_OVERLAP = 150

# ── Embeddings model (downloaded once, cached locally) ────────────────────────

EMBED_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"


# ── Step 1: Extract ───────────────────────────────────────────────────────────

def extract_text(pdf_path: Path) -> tuple[str, dict]:
    """
    Extract text from a PDF.

    Strategy:
    1. Try Docling (structured Markdown, good for clean single-column PDFs).
    2. If Docling yields < 300 chars/page (sign of layout parsing failure),
       fall back to pdfminer which handles multi-column textbook layouts reliably.
    """
    log.info(f"Extracting: {pdf_path.name}")

    # ── Run both extractors, keep the one with more text ─────────────────────
    converter = DocumentConverter()
    result    = converter.convert(str(pdf_path))
    doc       = result.document
    docling_text = doc.export_to_markdown()
    num_pages    = len(doc.pages) if hasattr(doc, "pages") else 0

    pdfminer_text = _extract_with_pdfminer(pdf_path)

    log.info(f"Docling:  {len(docling_text):,} chars")
    log.info(f"pdfminer: {len(pdfminer_text):,} chars")

    if len(pdfminer_text) > len(docling_text) * 1.2:
        log.info("Using pdfminer (significantly more content extracted).")
        final_text = pdfminer_text
    else:
        log.info("Using Docling (comparable or better coverage).")
        final_text = docling_text

    metadata = {
        "source"   : pdf_path.name,
        "num_pages": num_pages,
    }

    log.info(f"Final extracted text: {len(final_text):,} characters")
    return final_text, metadata


def _extract_with_pdfminer(pdf_path: Path) -> str:
    """Plain text fallback via pdfminer — handles complex layouts Docling misses."""
    try:
        from pdfminer.high_level import extract_text as pm_extract
        text = pm_extract(str(pdf_path))
        log.info(f"pdfminer extracted {len(text):,} chars.")
        return text
    except ImportError:
        log.error("pdfminer not installed. Run: uv pip install pdfminer.six")
        raise


# ── Step 2: Chunk ─────────────────────────────────────────────────────────────

def chunk_text(text: str, base_metadata: dict) -> list[Document]:
    """
    Split extracted text into overlapping chunks.
    Each chunk becomes a LangChain Document with its own metadata.
    """
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n## ", "\n### ", "\n#### ", "\n\n", "\n", ". ", " "],
    )

    raw_chunks = splitter.split_text(text)

    documents = [
        Document(
            page_content=chunk,
            metadata={
                **base_metadata,
                "chunk_index": i,
            },
        )
        for i, chunk in enumerate(raw_chunks)
        if chunk.strip()   # skip empty chunks
    ]

    log.info(f"Split into {len(documents)} chunks  "
             f"(size={CHUNK_SIZE}, overlap={CHUNK_OVERLAP})")
    return documents


# ── Step 3: Embed + Index ─────────────────────────────────────────────────────

def build_faiss_index(documents: list[Document], book_id: str) -> Path:
    """
    Embed all chunks with HuggingFace and save a FAISS index to disk.
    Returns the path where the index was saved.
    """
    log.info(f"Loading embedding model: {EMBED_MODEL}")

    embeddings = HuggingFaceEmbeddings(
        model_name=EMBED_MODEL,
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True},
    )

    log.info("Embedding chunks and building FAISS index …")
    vectorstore = FAISS.from_documents(documents, embeddings)

    index_path = INDEXES_DIR / book_id
    vectorstore.save_local(str(index_path))

    log.info(f"FAISS index saved → {index_path}")
    return index_path


# ── Step 4: Persist metadata ──────────────────────────────────────────────────

def _load_store() -> dict:
    if STORE_FILE.exists():
        return json.loads(STORE_FILE.read_text())
    return {}


def _save_store(store: dict) -> None:
    STORE_FILE.write_text(json.dumps(store, indent=2))


def save_book_metadata(
    book_id: str,
    pdf_path: Path,
    num_pages: int,
    num_chunks: int,
) -> dict:
    """Persist book metadata to books.json."""
    store = _load_store()

    entry = {
        "id"          : book_id,
        "name"        : pdf_path.stem,          # filename without extension
        "filename"    : pdf_path.name,
        "num_pages"   : num_pages,
        "num_chunks"  : num_chunks,
        "index_path"  : str(INDEXES_DIR / book_id),
        "ingested_at" : datetime.now().isoformat(timespec="seconds"),
    }

    store[book_id] = entry
    _save_store(store)

    log.info(f"Metadata saved for '{entry['name']}' (id={book_id})")
    return entry


# ── Public API ────────────────────────────────────────────────────────────────

def ingest_book(pdf_path: str | Path) -> dict:
    """
    Full ingestion pipeline for a single PDF book.

    1. Extract structured text with Docling
    2. Split into chunks
    3. Embed with HuggingFace + save FAISS index to disk
    4. Persist metadata to books.json

    Returns the book metadata dict.
    """
    pdf_path = Path(pdf_path).resolve()

    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")
    if pdf_path.suffix.lower() != ".pdf":
        raise ValueError(f"Expected a .pdf file, got: {pdf_path.suffix}")

    book_id = uuid.uuid4().hex[:10]   # short unique id, e.g. "a3f9c12e01"

    log.info(f"{'─'*50}")
    log.info(f"Starting ingestion: {pdf_path.name}  (id={book_id})")
    log.info(f"{'─'*50}")

    # 1. Extract
    text, raw_meta = extract_text(pdf_path)

    # 2. Chunk
    documents = chunk_text(text, base_metadata={"source": pdf_path.name})

    # 3. Embed + index
    build_faiss_index(documents, book_id)

    # 4. Save metadata
    book = save_book_metadata(
        book_id   = book_id,
        pdf_path  = pdf_path,
        num_pages = raw_meta["num_pages"],
        num_chunks= len(documents),
    )

    log.info(f"{'─'*50}")
    log.info(f"Done! '{book['name']}' is ready to chat.")
    log.info(f"{'─'*50}")

    return book


# ── Helper: list all indexed books ────────────────────────────────────────────

def list_books() -> list[dict]:
    """Return all ingested books from books.json."""
    return list(_load_store().values())


def get_book(book_id: str) -> dict | None:
    """Return a single book's metadata by id."""
    return _load_store().get(book_id)


def delete_book(book_id: str) -> bool:
    """Remove a book's FAISS index and metadata entry."""
    import shutil

    store = _load_store()
    if book_id not in store:
        return False

    # Remove FAISS index folder
    index_path = Path(store[book_id]["index_path"])
    if index_path.exists():
        shutil.rmtree(index_path)
        log.info(f"Deleted index: {index_path}")

    del store[book_id]
    _save_store(store)
    log.info(f"Removed metadata for book id={book_id}")
    return True