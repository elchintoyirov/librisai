"""
llm.py — Ollama-powered RAG answering via the OpenAI-compatible API.

Console usage:
    from libris.llm import ask
    answer, source_docs = ask("Ibtidoiy jamoa tuzumi nima?", retriever)

API / streaming usage:
    from libris.llm import build_messages, stream_tokens
    source_docs, messages = build_messages(question, retriever)
    for token in stream_tokens(messages):
        yield token
"""

from openai import OpenAI

# ── Cached client (one per process) ──────────────────────────────────────────

_client: OpenAI | None = None

OLLAMA_BASE_URL = "http://localhost:11434/v1"
DEFAULT_MODEL   = "qwen2.5:7b"


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(base_url=OLLAMA_BASE_URL, api_key="ollama")
    return _client


# ── Query preprocessing ───────────────────────────────────────────────────────

# Question words that shift embeddings without adding semantic content
_QUESTION_WORDS = {
    # Uzbek
    "nima", "nima?", "nima:", "qanday", "qachon", "qaerda", "qaerga",
    "kim", "necha", "nega", "nimaga", "tushuntir", "tushuntiring",
    "haqida", "haqida?", "degani", "degan", "nedir", "bu",
    # English
    "what", "what's", "whats", "how", "when", "where", "who", "why",
    "is", "are", "was", "were", "explain", "define", "describe",
}

def _query_for_retrieval(question: str) -> str:
    """Strip question words so the embedding matches document content better."""
    tokens = question.rstrip("?").split()
    cleaned = [t for t in tokens if t.lower() not in _QUESTION_WORDS]
    return " ".join(cleaned) if cleaned else question


# ── Language detection ────────────────────────────────────────────────────────

def _detect_language(text: str) -> str:
    """Return a language instruction based on the script used in the text."""
    uzbek_chars = set("oʻgʼqhshchngOʻGʼQHShChNg")
    cyrillic    = sum(1 for c in text if "\u0400" <= c <= "\u04FF")
    latin_uzbek = sum(1 for c in text if c in uzbek_chars or c in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ")

    if cyrillic > 2:
        return "Javobni O'ZBEK tilida, LOTIN yozuvida yoz."
    if latin_uzbek > 2:
        return "Javobni O'ZBEK tilida, LOTIN yozuvida yoz."
    return "Answer in English."


# ── System prompt ─────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """\
Sen Libris AI — o'quvchilarga yordam beruvchi o'quv yordamchisisiz.
Faqat foydalanuvchi xabaridagi darslik parchalaridan foydalanib javob ber.
Savollarga kamida 2-3 jumla bilan tushuntirma javob ber — faqat sarlavha yoki kalit so'z yozma.
Agar parcha javobni o'z ichiga olmasa, shunday de: "Bu mavzu darslikda yo'q."
Til qoidasi: savol o'zbek tilida bo'lsa, faqat o'zbek lotin yozuvida javob ber."""


# ── Public API ────────────────────────────────────────────────────────────────

def ask(
    question: str,
    retriever,
    model: str = DEFAULT_MODEL,
) -> tuple[str, list]:
    """
    Retrieve relevant chunks and stream Claude's answer to stdout.

    Returns (answer_text, source_docs).
    """
    # 1. Retrieve context — use cleaned query for better embedding match
    retrieval_query = _query_for_retrieval(question)
    source_docs = retriever.invoke(retrieval_query)
    context = "\n\n---\n\n".join(doc.page_content for doc in source_docs)

    # 2. Detect language and embed instruction directly in the user message
    #    (small models follow user-turn instructions more reliably than system)
    lang_instruction = _detect_language(question)

    user_content = (
        f"{lang_instruction}\n\n"
        f"Textbook excerpts:\n{context}\n\n"
        f"Question: {question}"
    )

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user",   "content": user_content},
    ]

    # 3. Stream
    client = _get_client()
    answer_parts: list[str] = []

    with client.chat.completions.create(
        model=model,
        messages=messages,
        max_tokens=1024,
        temperature=0,
        stream=True,
    ) as stream:
        for chunk in stream:
            delta = chunk.choices[0].delta
            if delta.content:
                print(delta.content, end="", flush=True)
                answer_parts.append(delta.content)

    print()
    return "".join(answer_parts), source_docs


# ── API helpers ───────────────────────────────────────────────────────────────

def build_messages(
    question: str,
    retriever,
    history: list[dict] | None = None,
) -> tuple[list, list]:
    """
    Build the LLM message list for a question + optional chat history.

    Returns (source_docs, messages).
    The caller can pass messages to stream_tokens() or use them directly.
    History items must be {"role": "user"|"assistant", "content": "..."}.
    """
    retrieval_query = _query_for_retrieval(question)
    source_docs     = retriever.invoke(retrieval_query)
    context         = "\n\n---\n\n".join(doc.page_content for doc in source_docs)
    lang_instruction = _detect_language(question)

    user_content = (
        f"{lang_instruction}\n\n"
        f"Textbook excerpts:\n{context}\n\n"
        f"Question: {question}"
    )

    messages: list[dict] = [{"role": "system", "content": SYSTEM_PROMPT}]
    if history:
        messages.extend(history)
    messages.append({"role": "user", "content": user_content})

    return source_docs, messages


def stream_tokens(messages: list[dict], model: str = DEFAULT_MODEL):
    """
    Yield answer tokens one-by-one from Ollama.
    Designed for use with FastAPI StreamingResponse.
    """
    client = _get_client()
    with client.chat.completions.create(
        model=model,
        messages=messages,
        max_tokens=1024,
        temperature=0,
        stream=True,
    ) as stream:
        for chunk in stream:
            delta = chunk.choices[0].delta
            if delta.content:
                yield delta.content
