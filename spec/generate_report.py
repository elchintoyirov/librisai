"""
generate_report.py — Generate Libris AI project implementation PDF
                     in TATU academic report style (matching sample.pdf).
Run: python spec/generate_report.py   (from project root)
  or cd spec && python generate_report.py
"""

from pathlib import Path
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer,
    HRFlowable, PageBreak, Image, ListFlowable, ListItem,
    Preformatted, Table, TableStyle,
)
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY

HERE      = Path(__file__).parent          # spec/
OUTPUT    = str(HERE / "Libris_AI_Implementation_Report.pdf")
LOGO_PATH = str(HERE / "tatu_logo.jpeg")
SWAGGER   = str(HERE / "swagger_ui.png")
WEBUI     = str(HERE / "web_ui.png")
RED       = colors.HexColor("#CC0000")
BLACK     = colors.black
GRAY      = colors.HexColor("#555555")

W = A4[0] - 4*cm   # usable width

# ── Styles (Times-Roman to match academic sample) ─────────────────────────────
def S(name, **kw):
    return ParagraphStyle(name, **kw)

COVER_INST  = S("ci", fontName="Times-Bold",   fontSize=12, alignment=TA_CENTER,
                leading=18, spaceAfter=4, textColor=BLACK)
COVER_FAC   = S("cf", fontName="Times-Bold",   fontSize=12, alignment=TA_CENTER,
                leading=18, spaceAfter=2, textColor=BLACK)
COVER_RED   = S("cr", fontName="Times-Bold",   fontSize=12, alignment=TA_CENTER,
                leading=18, spaceAfter=2, textColor=RED)
COVER_BODY  = S("cb", fontName="Times-Roman",  fontSize=12, alignment=TA_CENTER,
                leading=18, spaceAfter=4, textColor=BLACK)
COVER_LEFT  = S("cl", fontName="Times-Bold",   fontSize=12, alignment=TA_LEFT,
                leading=20, spaceAfter=2, textColor=BLACK)
COVER_ITEM  = S("cit",fontName="Times-Roman",  fontSize=12, alignment=TA_LEFT,
                leading=20, spaceAfter=0, leftIndent=28, textColor=BLACK)
COVER_FOOT  = S("cft",fontName="Times-Bold",   fontSize=12, alignment=TA_CENTER,
                leading=18, spaceAfter=0, textColor=BLACK)

TITLE_PAGE  = S("tp", fontName="Times-Bold",   fontSize=13, alignment=TA_CENTER,
                leading=20, spaceAfter=14, textColor=BLACK)

H1   = S("h1", fontName="Times-Bold",   fontSize=12, alignment=TA_LEFT,
          leading=20, spaceBefore=14, spaceAfter=6, textColor=BLACK)
H2   = S("h2", fontName="Times-Bold",   fontSize=12, alignment=TA_LEFT,
          leading=20, spaceBefore=10, spaceAfter=4, textColor=BLACK)
BODY = S("bd", fontName="Times-Roman",  fontSize=12, alignment=TA_JUSTIFY,
          leading=20, spaceAfter=8, textColor=BLACK)
BODI = S("bi", fontName="Times-Italic", fontSize=12, alignment=TA_JUSTIFY,
          leading=20, spaceAfter=8, textColor=BLACK)

def h1(text):   return Paragraph(text, H1)
def h2(text):   return Paragraph(text, H2)
def p(text):    return Paragraph(text, BODY)
def sp(n=10):   return Spacer(1, n)
def hr():       return HRFlowable(width="100%", thickness=0.5,
                                  color=colors.HexColor("#cccccc"), spaceAfter=6)

CODE = S("code", fontName="Courier", fontSize=8, leading=11,
         textColor=colors.HexColor("#1a1a1a"))

def code_block(code_text: str, caption: str = "") -> list:
    """Render a monospace code snippet inside a shaded box."""
    pre = Preformatted(code_text, CODE)
    tbl = Table([[pre]], colWidths=[W])
    tbl.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), colors.HexColor("#f4f4f4")),
        ("BOX",           (0, 0), (-1, -1), 0.5, colors.HexColor("#bbbbbb")),
        ("TOPPADDING",    (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING",   (0, 0), (-1, -1), 8),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 8),
    ]))
    result = []
    if caption:
        result.append(Paragraph(f"<i>{caption}</i>", BODY))
        result.append(sp(2))
    result.append(tbl)
    result.append(sp(8))
    return result


def endpoint_table(rows):
    """
    Render a clean, monochrome API endpoint summary table.
    rows: list of (method, endpoint, description) tuples.
    """
    COL = [1.8 * cm, 5.0 * cm, W - 6.8 * cm]

    _TH = ParagraphStyle("_th", fontName="Times-Bold",   fontSize=10,
                          textColor=BLACK, leading=14)
    _MT = ParagraphStyle("_mt", fontName="Courier-Bold", fontSize=9,
                          textColor=BLACK, leading=12)
    _RT = ParagraphStyle("_rt", fontName="Courier",      fontSize=9,
                          textColor=BLACK, leading=12)
    _DS = ParagraphStyle("_ds", fontName="Times-Roman",  fontSize=10,
                          textColor=BLACK, leading=14)

    data = [[Paragraph("Method", _TH),
             Paragraph("Endpoint", _TH),
             Paragraph("Description", _TH)]]
    for method, endpoint, desc in rows:
        data.append([
            Paragraph(method, _MT),
            Paragraph(endpoint, _RT),
            Paragraph(desc, _DS),
        ])

    style = [
        # Header row — light gray background, bold text
        ("BACKGROUND",    (0, 0), (-1,  0), colors.HexColor("#e0e0e0")),
        ("LINEBELOW",     (0, 0), (-1,  0), 1.0, BLACK),
        # Alternating row shading — very subtle
        ("ROWBACKGROUNDS",(0, 1), (-1, -1),
         [colors.white, colors.HexColor("#f7f7f7")]),
        # Borders
        ("BOX",           (0, 0), (-1, -1), 0.8, BLACK),
        ("INNERGRID",     (0, 0), (-1, -1), 0.4, colors.HexColor("#aaaaaa")),
        # Alignment and padding
        ("ALIGN",         (0, 0), ( 0, -1), "CENTER"),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING",    (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING",   (0, 0), (-1, -1), 8),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 8),
    ]
    tbl = Table(data, colWidths=COL)
    tbl.setStyle(TableStyle(style))
    return tbl


def bullet(items):
    """Bulleted list matching sample.pdf style."""
    entries = []
    for text in items:
        entries.append(ListItem(Paragraph(text, BODY), bulletColor=BLACK,
                                leftIndent=28, bulletIndent=10))
    return ListFlowable(entries, bulletType="bullet", bulletFontName="Times-Roman",
                        bulletFontSize=12, start="•", spaceAfter=4)

def numbered(items):
    """Numbered list matching sample.pdf style."""
    entries = []
    for text in items:
        entries.append(ListItem(Paragraph(text, BODY), leftIndent=36, bulletIndent=10))
    return ListFlowable(entries, bulletType="1", bulletFontName="Times-Roman",
                        bulletFontSize=12, spaceAfter=4)


# ── Cover page ────────────────────────────────────────────────────────────────
def cover_page():
    logo = Image(LOGO_PATH, width=6*cm, height=6*cm)
    logo.hAlign = "CENTER"
    return [
        sp(30),
        Paragraph("MINISTRY FOR DEVELOPMENT OF INFORMATION TECHNOLOGIES<br/>"
                  "AND COMMUNICATIONS OF THE REPUBLIC OF UZBEKISTAN", COVER_INST),
        sp(6),
        Paragraph("MUHAMMAD AL-KHWARIZMI TASHKENT UNIVERSITY OF<br/>"
                  "INFORMATION TECHNOLOGIES", COVER_INST),
        sp(14),
        Paragraph("Faculty: Software Engineering", COVER_FAC),
        Paragraph("Project Implementation", COVER_RED),
        Paragraph("Fundamentals of Artificial Intelligence", COVER_FAC),
        sp(18),
        logo,
        sp(22),
        Paragraph("Completed:", COVER_LEFT),
        Paragraph("1. Saidaliyev Diyorxo'ja", COVER_ITEM),
        Paragraph("2. Mullaboyev Og'abek",    COVER_ITEM),
        Paragraph("3. Axmedova Kamola",        COVER_ITEM),
        Paragraph("4. Toyirov Elchin",         COVER_ITEM),
        Paragraph("5. Yhlasov Kyyas",          COVER_ITEM),
        sp(10),
        Paragraph("Group: 3",                         COVER_LEFT),
        Paragraph("Professor: Muxiddinov Muhriddin",  COVER_LEFT),
        sp(14),
        Paragraph("Source Code: github.com/elchintoyirov/librisai", COVER_LEFT),
        sp(16),
        Paragraph("Tashkent - 2026", COVER_FOOT),
        PageBreak(),
    ]


# ── Content ───────────────────────────────────────────────────────────────────
def content():
    s = []

    # ── Page header ───────────────────────────────────────────────────────────
    s += [Paragraph("Libris AI — Academic Textbook Assistant", TITLE_PAGE)]

    # ── 1. Problem Statement ──────────────────────────────────────────────────
    s += [h1("1. Problem Statement & Real-World Relevance")]
    s += [p("<b>The Problem:</b> Students and researchers in Uzbekistan often face a "
            "\"knowledge gap\" due to two main factors:")]
    s += [numbered([
        "<b>Static Content:</b> Traditional textbooks are \"flat\" files. Finding "
        "specific information requires manual skimming or simple keyword searches "
        "that fail to capture context or complex concepts.",
        "<b>Language Barrier:</b> High-quality academic resources are frequently "
        "published in English or Russian. Even when Uzbek resources exist, there is "
        "a lack of advanced AI tools optimized for the Uzbek language's unique "
        "grammatical structure (agglutination).",
    ])]
    s += [p("<b>Real-World Relevance:</b> In the 2026 academic landscape, accessibility "
            "is key. Libris AI democratizes education by allowing a student in a remote "
            "region of Uzbekistan to \"talk\" to a world-class History or Law textbook "
            "in their native tongue. This reduces the time spent on rote searching and "
            "increases time spent on critical thinking and synthesis.")]

    # ── 2. Objectives ─────────────────────────────────────────────────────────
    s += [h1("2. Project Objectives & Expected Outcomes")]
    s += [h2("Objectives:")]
    s += [bullet([
        "<b>Semantic Indexing:</b> To convert PDF text into high-dimensional mathematical "
        "vectors that represent the <i>meaning</i> of the content, not just the words.",
        "<b>Cross-Lingual Retrieval:</b> To enable the system to understand a query in "
        "Uzbek and accurately find the corresponding answer within a textbook, regardless "
        "of the source language.",
        "<b>Contextual Summarization:</b> To provide concise, accurate answers instead "
        "of just pointing to a page number.",
        "<b>Offline Operation:</b> To run the entire system locally with no cloud API "
        "calls — ensuring data privacy and accessibility in low-connectivity environments.",
    ])]
    s += [h2("Expected Outcomes:")]
    s += [bullet([
        "A <b>Searchable Knowledge Base</b> that responds to natural language questions "
        "(e.g., <i>\"Ibtidoiy jamoa tuzumi nima?\"</i> — What is the primitive communal system?).",
        "<b>Increased Learning Efficiency:</b> A measurable reduction in the time required "
        "for students to extract specific data from large volumes of textbook text.",
        "<b>Language Inclusivity:</b> A functional AI tool that respects and utilizes the "
        "Uzbek language — both Latin and Cyrillic scripts — in a sophisticated academic context.",
    ])]

    # ── 3. RAG Technique ──────────────────────────────────────────────────────
    s += [h1("3. The AI Technique: Retrieval-Augmented Generation (RAG)")]
    s += [p("The primary technique used is <b>Retrieval-Augmented Generation (RAG)</b>. "
            "This is a multi-step NLP process:")]
    s += [numbered([
        "<b>Document Chunking & Embedding:</b> The PDF is broken into small overlapping "
        "segments (800 characters, 150-character overlap). Each segment is converted into "
        "a 384-dimensional vector using a multilingual <b>Embedding Model</b> "
        "(paraphrase-multilingual-MiniLM-L12-v2).",
        "<b>Hybrid Index Storage:</b> The vectors are stored in a <b>FAISS</b> index for "
        "semantic search, and in a <b>BM25</b> keyword index for exact token matching. "
        "Both indexes act as the long-term memory of the textbook.",
        "<b>Hybrid Semantic Search:</b> When a user asks a question in Uzbek, the system "
        "converts it into a vector and simultaneously queries both indexes. Results are "
        "merged using <b>Reciprocal Rank Fusion (RRF)</b>, producing a final ranked list "
        "of the most relevant textbook passages.",
        "<b>Generative Response:</b> The retrieved passages and the original question are "
        "fed into a <b>Large Language Model (LLM)</b> running locally via Ollama "
        "(qwen2.5:7b). The LLM uses only the retrieved textbook data to write an answer "
        "in natural-sounding Uzbek Latin script.",
    ])]
    s += [h2("Why RAG?")]
    s += [p("Unlike a standard chatbot (which might \"hallucinate\" or make up facts), a "
            "<b>RAG</b> system is grounded. It <i>must</i> use the textbook provided as "
            "its only source of truth. This ensures the academic integrity required for a "
            "textbook assistant. With <b>temperature=0</b>, the model is fully "
            "deterministic — it gives the same answer every time and consistently says "
            "\"Bu mavzu darslikda yo'q\" (This topic is not in the textbook) when the "
            "content is absent, rather than inventing a response.")]

    s += [PageBreak()]

    # ── 4. System Architecture ────────────────────────────────────────────────
    s += [Paragraph("Libris AI — Academic Textbook Assistant", TITLE_PAGE)]
    s += [h1("4. System Architecture & Implementation")]
    s += [p("Libris AI is composed of four Python modules and two distinct operational "
            "phases: an offline <b>ingestion pipeline</b> that processes a PDF into a "
            "searchable index, and an online <b>query pipeline</b> that retrieves and "
            "generates answers.")]

    s += [h2("Project File Structure:")]
    s += [bullet([
        "<b>main.py</b> — Console entry point. Verifies Ollama is running, manages book "
        "selection, and drives the chat loop with commands: /books, /add, /switch, "
        "/clear, /help, /quit.",
        "<b>libris/ingest.py</b> — Full ingestion pipeline. Runs PDF extraction, "
        "text chunking, HuggingFace embedding, and FAISS index creation. Persists "
        "book metadata to data/books.json.",
        "<b>libris/retriever.py</b> — Implements HybridRetriever using BM25 and FAISS "
        "with Reciprocal Rank Fusion. Loads the FAISS index from disk on startup.",
        "<b>libris/llm.py</b> — Handles query preprocessing, language detection, "
        "prompt construction, and streaming LLM responses via Ollama.",
        "<b>libris/store.py</b> — Thin re-export of book metadata helpers "
        "(list_books, get_book, delete_book).",
    ])]

    s += [h2("Ingestion Pipeline — Best-of-Two Extraction:")]
    s += [p("The most significant engineering challenge in this project was PDF extraction. "
            "The Uzbek history textbook (192 pages, two-column layout) yielded only "
            "<b>68,000 characters</b> from Docling due to layout parsing failures, while "
            "pdfminer.six extracted <b>280,659 characters</b> — a 4× difference. Nineteen "
            "textbook chapters were completely absent from the Docling index.")]
    s += [p("The solution runs both extractors on every PDF and automatically selects "
            "the one with more content. If pdfminer yields more than 120% of Docling's "
            "output, pdfminer is used. This is transparent to the user and requires no "
            "configuration.")]

    s += [h2("Hybrid Retrieval — BM25 + FAISS + RRF:")]
    s += [p("A single retrieval strategy is insufficient for Uzbek textbooks. Two "
            "complementary approaches are combined:")]
    s += [bullet([
        "<b>BM25 (weight 0.6):</b> Probabilistic keyword retrieval based on TF-IDF "
        "with document-length normalisation. Essential for proper nouns — "
        "\"Bobil\" (Babylon), \"Aleksandr\", \"Xorazm\" — which have high IDF weight "
        "and are matched exactly regardless of semantic context.",
        "<b>FAISS (weight 0.4):</b> Approximate nearest-neighbor search in "
        "384-dimensional embedding space. Handles conceptual queries where words differ "
        "between question and document — e.g., \"ibtidoiy jamoa tuzumi\" retrieves "
        "relevant chunks even when phrased differently in the textbook.",
    ])]
    s += [p("Results from both retrievers are merged using <b>Reciprocal Rank Fusion</b>: "
            "each document receives a score proportional to its rank in each list "
            "(score = weight / (60 + rank + 1)), and the top 6 documents by combined "
            "score are passed to the LLM.")]

    # ── Code Walkthrough ──────────────────────────────────────────────────────
    s += [h2("Code: Step 1 — Best-of-Two PDF Extraction  (libris/ingest.py)")]
    s += code_block(
        "# Run both extractors; the one with more content is used.\n"
        "converter    = DocumentConverter()\n"
        "docling_text = converter.convert(str(pdf_path)).document.export_to_markdown()\n"
        "pdfminer_text = pm_extract(str(pdf_path))\n"
        "\n"
        "if len(pdfminer_text) > len(docling_text) * 1.2:\n"
        "    final_text = pdfminer_text   # wins on two-column textbook layouts\n"
        "else:\n"
        "    final_text = docling_text    # wins on clean single-column PDFs",
        "The 1.2 threshold absorbs small formatting differences; a 4× gap "
        "(68K vs 280K chars) triggers pdfminer for the history textbook.",
    )

    s += [h2("Code: Step 2 — Overlapping Text Chunking  (libris/ingest.py)")]
    s += code_block(
        "splitter = RecursiveCharacterTextSplitter(\n"
        '    chunk_size=800,        # ~150 words — fits comfortably in LLM context\n'
        '    chunk_overlap=150,     # 19% overlap prevents sentence loss at boundaries\n'
        '    separators=["\\n## ", "\\n### ", "\\n\\n", "\\n", ". ", " "],\n'
        ")\n"
        "documents = [\n"
        "    Document(\n"
        '        page_content=chunk,\n'
        '        metadata={"source": pdf_path.name, "chunk_index": i},\n'
        "    )\n"
        "    for i, chunk in enumerate(splitter.split_text(text))\n"
        "    if chunk.strip()   # discard whitespace-only chunks\n"
        "]",
        "Separators are tried left-to-right: section headers split first, "
        "then paragraphs, then sentences — preserving semantic boundaries.",
    )

    s += [h2("Code: Step 3 — HuggingFace Embedding & FAISS Index  (libris/ingest.py)")]
    s += code_block(
        "embeddings = HuggingFaceEmbeddings(\n"
        '    model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",\n'
        '    model_kwargs={"device": "cpu"},\n'
        '    encode_kwargs={"normalize_embeddings": True},  # cosine-ready vectors\n'
        ")\n"
        "\n"
        "# Each chunk -> 384-dimensional unit vector; index persisted to disk\n"
        "vectorstore = FAISS.from_documents(documents, embeddings)\n"
        "vectorstore.save_local(str(INDEXES_DIR / book_id))",
        "Normalized embeddings allow cosine similarity to be computed as a "
        "dot product, which FAISS performs with its IndexFlatIP index.",
    )

    s += [h2("Code: Step 4 — Hybrid RRF Retrieval  (libris/retriever.py)")]
    s += code_block(
        "bm25_docs  = self.bm25.invoke(query)            # exact keyword match\n"
        "faiss_docs = self.faiss_retriever.invoke(query) # semantic similarity\n"
        "\n"
        "scores: dict[str, float] = {}\n"
        "for rank, doc in enumerate(bm25_docs):          # BM25 weight = 0.6\n"
        "    scores[doc.page_content] = (\n"
        "        scores.get(doc.page_content, 0)\n"
        "        + self.bm25_weight / (self.rrf_k + rank + 1)\n"
        "    )\n"
        "for rank, doc in enumerate(faiss_docs):         # FAISS weight = 0.4\n"
        "    scores[doc.page_content] = (\n"
        "        scores.get(doc.page_content, 0)\n"
        "        + self.faiss_weight / (self.rrf_k + rank + 1)\n"
        "    )\n"
        "ranked = sorted(scores, key=scores.__getitem__, reverse=True)\n"
        "return [id_to_doc[k] for k in ranked[:self.k]]  # top-6 chunks",
        "A document that appears in both BM25 and FAISS results accumulates "
        "scores from each ranker — consensus chunks are strongly preferred.",
    )

    s += [h2("Code: Step 5 — Language Detection & RAG Prompt  (libris/llm.py)")]
    s += code_block(
        "SYSTEM_PROMPT = (\n"
        "    \"Sen Libris AI — o'quvchilarga yordam beruvchi o'quv yordamchisisiz.\\n\"\n"
        "    \"Faqat darslik parchalaridan foydalanib javob ber.\\n\"\n"
        "    \"Agar parcha javobni o'z ichiga olmasa: 'Bu mavzu darslikda yo\\'q.'\"\n"
        ")\n"
        "\n"
        "def _detect_language(text: str) -> str:\n"
        '    cyrillic = sum(1 for c in text if "\\u0400" <= c <= "\\u04FF")\n'
        "    if cyrillic > 2:\n"
        "        return \"Javobni O'ZBEK tilida, LOTIN yozuvida yoz.\"\n"
        '    return "Answer in English."\n'
        "\n"
        "# Build messages and stream answer (temperature=0 for determinism)\n"
        "source_docs = retriever.invoke(_query_for_retrieval(question))\n"
        'context     = "\\n\\n---\\n\\n".join(d.page_content for d in source_docs)\n'
        "messages    = [\n"
        '    {"role": "system", "content": SYSTEM_PROMPT},\n'
        '    {"role": "user",   "content": f"{_detect_language(question)}\\n\\n"\n'
        '                                  f"Textbook excerpts:\\n{context}\\n\\n"\n'
        '                                  f"Question: {question}"},\n'
        "]",
        "temperature=0 makes generation deterministic: the model consistently "
        "acknowledges missing content instead of hallucinating an answer.",
    )

    s += [PageBreak()]

    # ── 5. REST API Layer ─────────────────────────────────────────────────────
    s += [Paragraph("Libris AI — Academic Textbook Assistant", TITLE_PAGE)]
    s += [h1("5. REST API Layer  (api.py)")]
    s += [p("In addition to the console application, Libris AI exposes a full "
            "<b>RESTful HTTP API</b> built with <b>FastAPI</b>. Start it with "
            "<b>uvicorn api:app --reload</b>; the interactive Swagger UI is then "
            "auto-generated at <b>http://localhost:8000/docs</b>.")]

    # Swagger UI screenshot
    swagger_img = Image(SWAGGER, width=W, height=W * 0.52)
    swagger_img.hAlign = "CENTER"
    s += [sp(6), swagger_img]
    s += [Paragraph(
        "<i>Figure 1: Auto-generated Swagger UI showing all five endpoints and "
        "Pydantic schema definitions (localhost:8000/docs).</i>",
        S("cap", fontName="Times-Italic", fontSize=10, alignment=TA_CENTER,
          leading=14, spaceAfter=8, textColor=GRAY),
    )]
    s += [sp(4)]

    s += [p("The API cleanly separates the retrieval and generation logic from any "
            "specific user interface. The same backend can serve a web frontend, "
            "a Telegram bot, or a mobile client without modification. All state is "
            "stateless per-request — conversation history is passed by the caller "
            "rather than stored server-side.")]

    s += [h2("5.1  Endpoint Overview")]
    s += [endpoint_table([
        ("GET",    "/books",
         "Return a JSON array of all indexed books with their metadata "
         "(id, name, page count, chunk count, ingestion timestamp)."),
        ("POST",   "/books/upload",
         "Accept a multipart PDF upload, save it to a temp file, run the full "
         "ingestion pipeline (extract → chunk → embed → FAISS index), "
         "and return the new book's metadata."),
        ("DELETE", "/books/{book_id}",
         "Remove the book's FAISS index folder from disk, evict its retriever "
         "from the in-memory cache, and delete its entry from books.json."),
        ("POST",   "/chat",
         "Blocking single-turn chat. Retrieves context chunks, calls the LLM, "
         "collects all tokens, and returns the complete answer plus source "
         "chunk indices in a single JSON response."),
        ("POST",   "/chat/stream",
         "Streaming chat via Server-Sent Events (SSE). Yields tokens one-by-one "
         "as they are generated, then emits a sources event and a done event "
         "to signal end-of-stream."),
    ])]
    s += [sp(4)]

    s += [h2("5.2  Pydantic Request / Response Schemas")]
    s += code_block(
        "class Message(BaseModel):\n"
        "    role:    str   # 'user' or 'assistant'\n"
        "    content: str\n"
        "\n"
        "class ChatRequest(BaseModel):\n"
        "    book_id:  str\n"
        "    question: str\n"
        "    history:  list[Message] = []  # full conversation (stateless API)\n"
        "\n"
        "class ChatResponse(BaseModel):\n"
        "    answer:  str\n"
        "    sources: list[int]            # FAISS chunk indices",
        "ChatRequest carries the entire conversation history on every call — "
        "the server holds no session state between requests.",
    )

    s += [h2("5.3  Retriever Cache  — avoiding the 2-second cold start")]
    s += code_block(
        "@app.on_event('startup')\n"
        "def startup():\n"
        "    app.state.retrievers: dict = {}  # book_id -> HybridRetriever\n"
        "\n"
        "def _get_retriever(book_id: str):\n"
        "    \"\"\"Load FAISS index from disk on first access; return cached on later calls.\"\"\"\n"
        "    if book_id not in app.state.retrievers:\n"
        "        book = get_book(book_id)\n"
        "        if book is None:\n"
        "            raise HTTPException(404, detail=f\"Book '{book_id}' not found.\")\n"
        "        app.state.retrievers[book_id] = load_retriever(book['index_path'])\n"
        "    return app.state.retrievers[book_id]",
        "The FAISS index load (disk read + numpy deserialization) takes ~2 seconds. "
        "Caching means only the first question per book pays this cost.",
    )

    s += [PageBreak()]
    s += [Paragraph("Libris AI — Academic Textbook Assistant", TITLE_PAGE)]

    s += [h2("5.4  POST /books/upload — PDF Ingestion Endpoint")]
    s += code_block(
        "@app.post('/books/upload', summary='Upload and ingest a PDF textbook')\n"
        "def upload_book(file: UploadFile = File(...)):\n"
        "    if not file.filename.endswith('.pdf'):\n"
        "        raise HTTPException(400, detail='Only PDF files are accepted.')\n"
        "\n"
        "    # Save the uploaded bytes to a temp file, then run the pipeline\n"
        "    with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:\n"
        "        shutil.copyfileobj(file.file, tmp)\n"
        "        tmp_path = Path(tmp.name)\n"
        "    try:\n"
        "        book = ingest_book(tmp_path)   # extract -> chunk -> embed -> index\n"
        "    finally:\n"
        "        tmp_path.unlink(missing_ok=True)  # always clean up the temp file\n"
        "\n"
        "    return book   # JSON: {id, name, num_pages, num_chunks, ingested_at}",
        "The temp-file pattern avoids holding the entire PDF in memory and ensures "
        "cleanup even if ingestion raises an exception.",
    )

    s += [h2("5.5  POST /chat — Blocking Single-Turn Response")]
    s += code_block(
        "@app.post('/chat', response_model=ChatResponse)\n"
        "def chat(req: ChatRequest):\n"
        "    retriever = _get_retriever(req.book_id)\n"
        "    history   = [m.model_dump() for m in req.history]\n"
        "\n"
        "    # build_messages() runs hybrid retrieval + constructs the LLM prompt\n"
        "    source_docs, messages = build_messages(req.question, retriever, history)\n"
        "\n"
        "    # Collect all streamed tokens into a single string\n"
        "    answer  = ''.join(stream_tokens(messages))\n"
        "    sources = [doc.metadata.get('chunk_index', -1) for doc in source_docs]\n"
        "\n"
        "    return ChatResponse(answer=answer, sources=sources)",
        "Reuses the same stream_tokens() generator as the streaming endpoint — "
        "the only difference is collecting all tokens before responding.",
    )

    s += [h2("5.6  POST /chat/stream — Server-Sent Events")]
    s += [p("The streaming endpoint returns an <b>EventSource</b>-compatible "
            "SSE response. Each event is a JSON object on a <b>data:</b> line "
            "followed by a blank line. Three event types are emitted:")]
    s += [bullet([
        "<b>token</b> — one text fragment from the LLM, appended to the answer "
        "as it arrives. Allows the UI to render text progressively.",
        "<b>sources</b> — emitted once after the last token, carrying the list of "
        "FAISS chunk indices that were used to generate the answer.",
        "<b>done</b> — signals end of stream so the client can close the connection.",
    ])]
    s += code_block(
        "@app.post('/chat/stream')\n"
        "def chat_stream(req: ChatRequest):\n"
        "    retriever = _get_retriever(req.book_id)\n"
        "    source_docs, messages = build_messages(\n"
        "        req.question, retriever, [m.model_dump() for m in req.history]\n"
        "    )\n"
        "    sources = [doc.metadata.get('chunk_index', -1) for doc in source_docs]\n"
        "\n"
        "    def event_generator():\n"
        "        for token in stream_tokens(messages):\n"
        "            yield f\"data: {{'type': 'token', 'content': token}}\\n\\n\"\n"
        "        yield f\"data: {{'type': 'sources', 'content': sources}}\\n\\n\"\n"
        "        yield f\"data: {{'type': 'done'}}\\n\\n\"\n"
        "\n"
        "    return StreamingResponse(\n"
        "        event_generator(),\n"
        "        media_type='text/event-stream',\n"
        "        headers={'Cache-Control': 'no-cache', 'X-Accel-Buffering': 'no'},\n"
        "    )",
        "X-Accel-Buffering: no disables nginx response buffering when the API "
        "runs behind a reverse proxy, ensuring tokens reach the client immediately.",
    )

    s += [h2("5.7  SSE Wire Format & JavaScript Client Example")]
    s += code_block(
        "# Server sends (one line per event, blank line terminates each event):\n"
        "data: {\"type\": \"token\",   \"content\": \"Ibtidoiy\"}\n"
        "\n"
        "data: {\"type\": \"token\",   \"content\": \" jamoa\"}\n"
        "\n"
        "data: {\"type\": \"sources\", \"content\": [42, 47, 51]}\n"
        "\n"
        "data: {\"type\": \"done\"}\n",
        "The blank line between events is required by the SSE specification "
        "(RFC 6202). Each data: field is parsed independently by the browser.",
    )
    s += code_block(
        "// Minimal JavaScript EventSource client\n"
        "const es = new EventSource('/chat/stream');\n"
        "es.onmessage = e => {\n"
        "    const msg = JSON.parse(e.data);\n"
        "    if (msg.type === 'token')   appendText(msg.content);\n"
        "    if (msg.type === 'sources') showSources(msg.content);\n"
        "    if (msg.type === 'done')    es.close();\n"
        "};",
        "EventSource reconnects automatically on network errors — "
        "no extra client-side retry logic is needed.",
    )

    s += [PageBreak()]

    # ── 6. Web Frontend ───────────────────────────────────────────────────────
    s += [Paragraph("Libris AI — Academic Textbook Assistant", TITLE_PAGE)]
    s += [h1("6. Web Frontend  (static/)")]
    s += [p("Libris AI includes a lightweight single-page web application served "
            "from the <b>static/</b> folder — three files: "
            "<b>index.html</b>, <b>style.css</b>, and <b>app.js</b>. "
            "It is built with plain JavaScript (no framework) and communicates "
            "directly with the FastAPI backend at <b>localhost:8000</b>. "
            "Serve it with <b>uvicorn api:app --reload</b> and open "
            "<b>http://localhost:8000</b>.")]

    # Web UI screenshot
    webui_img = Image(WEBUI, width=W, height=W * 0.60)
    webui_img.hAlign = "CENTER"
    s += [sp(4), webui_img]
    s += [Paragraph(
        "<i>Figure 2: Web frontend — sidebar book list, streaming chat panel, "
        "and source chunk references (localhost:8000).</i>",
        S("cap2", fontName="Times-Italic", fontSize=10, alignment=TA_CENTER,
          leading=14, spaceAfter=10, textColor=GRAY),
    )]

    s += [h2("6.1  Layout: Two-Panel Design")]
    s += [bullet([
        "<b>Left sidebar (200 px):</b> Brand header, \u201c+ Add Textbook\u201d file-picker "
        "button, and a scrollable list of all indexed books. Each book entry "
        "shows its name, page count, and a delete (\u2715) button.",
        "<b>Right main panel:</b> When no book is selected, an empty-state prompt "
        "is shown. Once a book is selected, the panel switches to a chat view with "
        "a fixed header (book title + page/chunk count), a scrollable message list, "
        "and an auto-growing textarea input bar with a Send button.",
        "<b>Source tags:</b> Every AI reply shows coloured <i>chunk N</i> badges "
        "below the answer bubble, indicating exactly which FAISS chunks were used "
        "to generate the response.",
    ])]

    s += [h2("6.2  PDF Upload Flow  (static/app.js)")]
    s += code_block(
        "fileInput.addEventListener('change', async () => {\n"
        "    const file = fileInput.files[0];\n"
        "\n"
        "    // Build multipart form and POST to /books/upload\n"
        "    const form = new FormData();\n"
        "    form.append('file', file);\n"
        "    const book = await api('/books/upload', { method: 'POST', body: form });\n"
        "\n"
        "    toast(`\"${book.name}\" ready — ${book.num_chunks} chunks.`, 'success');\n"
        "    await loadBooks();   // refresh sidebar list\n"
        "    selectBook(book);    // immediately open the new book for chat\n"
        "});",
        "selectBook() resets history, updates the header, and appends the "
        "greeting message — so the user can start asking questions immediately "
        "after the upload completes.",
    )

    s += [h2("6.3  Real-Time SSE Streaming  (static/app.js)")]
    s += [p("The frontend reads the <b>/chat/stream</b> response as a "
            "<b>ReadableStream</b> — avoiding EventSource so the POST body "
            "(book_id, question, history) can be sent as JSON. "
            "Tokens are appended to the bubble as they arrive; the blinking "
            "cursor is removed once the <b>sources</b> event lands.")]
    s += code_block(
        "const res    = await fetch(`${API}/chat/stream`, {\n"
        "    method: 'POST',\n"
        "    headers: { 'Content-Type': 'application/json' },\n"
        "    body: JSON.stringify({ book_id: state.activeBook.id,\n"
        "                           question, history: state.history }),\n"
        "});\n"
        "const reader  = res.body.getReader();\n"
        "const decoder = new TextDecoder();\n"
        "let   buf     = '';\n"
        "\n"
        "while (true) {\n"
        "    const { done, value } = await reader.read();\n"
        "    if (done) break;\n"
        "    buf += decoder.decode(value, { stream: true });\n"
        "    const lines = buf.split('\\n');\n"
        "    buf = lines.pop();          // hold incomplete line in buffer\n"
        "\n"
        "    for (const line of lines) {\n"
        "        if (!line.startsWith('data: ')) continue;\n"
        "        const evt = JSON.parse(line.slice(6));\n"
        "        if (evt.type === 'token')   textEl.innerHTML = fmt(answer += evt.content);\n"
        "        if (evt.type === 'sources') renderSourceTags(evt.content);\n"
        "        if (evt.type === 'done')    cursor?.remove();\n"
        "    }\n"
        "}",
        "The incomplete-line buffer (buf = lines.pop()) is essential: "
        "a TCP packet may split an SSE data: line mid-way, "
        "and the remainder must be prepended to the next chunk.",
    )

    s += [h2("6.4  Conversation History & Light Markdown  (static/app.js)")]
    s += code_block(
        "// After stream completes — append Q&A pair to in-memory history\n"
        "state.history.push({ role: 'user',      content: question });\n"
        "state.history.push({ role: 'assistant', content: answer   });\n"
        "\n"
        "// Cap at last 10 exchanges (20 messages) to avoid prompt overflow\n"
        "if (state.history.length > 20) state.history = state.history.slice(-20);\n"
        "\n"
        "// Minimal Markdown renderer — bold, italic, newlines only\n"
        "function fmt(text) {\n"
        "    return esc(text)\n"
        "        .replace(/\\*\\*(.+?)\\*\\*/g, '<strong>$1</strong>')\n"
        "        .replace(/\\*(.+?)\\*/g,     '<em>$1</em>')\n"
        "        .replace(/\\n/g,            '<br>');\n"
        "}",
        "History is passed on every request (stateless API design). "
        "The 20-message cap prevents the LLM context window from overflowing "
        "during long study sessions.",
    )

    s += [PageBreak()]

    # ── 7. Language Challenges ────────────────────────────────────────────────
    s += [Paragraph("Libris AI — Academic Textbook Assistant", TITLE_PAGE)]
    s += [h1("7. Uzbek Language Engineering Challenges")]
    s += [p("Building an AI system for Uzbek presents challenges that do not exist for "
            "English or Russian systems. Each of the following was encountered and "
            "resolved during development:")]

    s += [h2("5.1 Two Active Scripts")]
    s += [p("Modern Uzbekistan officially uses Latin script (since 1993), but a significant "
            "portion of existing textbooks, digitized PDFs, and student input appears in "
            "Uzbek Cyrillic (Soviet-era). The system detects both scripts automatically "
            "and always instructs the LLM to respond in Latin script, regardless of the "
            "input script.")]

    s += [h2("5.2 Agglutinative Morphology")]
    s += [p("Uzbek builds words by stacking suffixes: \"podshoh\" (king) becomes "
            "\"podshohligi\" (his kingdom), \"podshohlarga\" (to the kings), "
            "\"podshohlikning\" (of the kingdom). BM25 treats these as entirely different "
            "tokens and cannot match them to the same root. Additionally, \"urug'\" means "
            "both <i>seed</i> (agricultural) and <i>clan</i> (historical), causing "
            "retrieval to return wrong context without morphological disambiguation. "
            "A Uzbek stemmer is listed as a future improvement.")]

    s += [h2("5.3 LLM Language Defaulting")]
    s += [p("Small local models (7–8B parameters) are highly sensitive to the language "
            "distribution of their context window. When retrieved chunks contain Cyrillic "
            "Uzbek text, models default to Russian. When the context is ambiguous, models "
            "default to their most common training language. Two techniques were combined "
            "to address this:")]
    s += [bullet([
        "<b>System prompt written in Uzbek</b> — conditioning the model's output language "
        "prior before any context is shown.",
        "<b>Explicit per-query language instruction</b> — \"Javobni O'ZBEK tilida, LOTIN "
        "yozuvida yoz\" injected at the top of every user message, in both Uzbek and "
        "positional emphasis.",
    ])]

    s += [h2("5.4 Hallucination on Missing Content")]
    s += [p("At default temperature (1.0), the model produced different wrong answers on "
            "each run when the topic was not in the textbook. Setting <b>temperature=0</b> "
            "makes generation fully deterministic: the model consistently acknowledges "
            "missing content rather than sampling from its parametric knowledge.")]

    # ── 6. Literature Review ──────────────────────────────────────────────────
    s += [h1("8. Literature Review — Existing AI/ML Approaches")]
    s += [p("In the last few years (2023–2026), the field of academic assistance has "
            "shifted from simple keyword-based search to <b>Contextual Intelligence</b>. "
            "Three main stages of development have led to the current state of the art:")]
    s += [bullet([
        "<b>Pre-2023 (Traditional NLP):</b> Systems relied heavily on rule-based "
        "processing and <b>TF-IDF</b> (Term Frequency-Inverse Document Frequency). "
        "While effective for keyword matching, these systems could not understand the "
        "\"intent\" behind a student's question. If a student used a synonym not present "
        "in the textbook, the system failed.",
        "<b>The Transformer Revolution (BERT & GPT):</b> The introduction of the "
        "Transformer architecture allowed for <b>Semantic Search</b>. Models like "
        "<b>mBERT</b> (Multilingual BERT) and <b>XLM-RoBERTa</b> enabled cross-lingual "
        "capabilities, meaning a system could potentially link an Uzbek query to an "
        "English source.",
        "<b>The RAG Era (2024–2026):</b> Retrieval-Augmented Generation (RAG) became "
        "the gold standard. It addresses the \"hallucination\" problem of LLMs by forcing "
        "the AI to retrieve actual excerpts from a specific PDF before generating an "
        "answer. This is critical for academic use where accuracy is non-negotiable.",
    ])]

    s += [h2("Key Models and Datasets")]
    s += [h2("A. Dominant Models")]
    s += [bullet([
        "<b>BERTbek & UzBERT:</b> Recent research (e.g., Kuriyozov et al., 2025) "
        "highlights that while multilingual models are good, monolingual models like "
        "<b>BERTbek</b> significantly outperform them in understanding Uzbek's complex "
        "morphology. Libris AI currently uses the multilingual MiniLM-L12 model; "
        "replacing it with a fine-tuned Uzbek model is a planned improvement.",
        "<b>GPT-4o & Llama 3.1/4:</b> These models serve as the \"Reasoning Engine\" in "
        "modern RAG systems. Libris AI uses the open-weight <b>qwen2.5:7b</b> model via "
        "Ollama, enabling fully offline operation at the cost of some output quality "
        "compared to GPT-4o.",
    ])]

    s += [h2("B. Key Datasets")]
    s += [bullet([
        "<b>UzTextbooks Dataset (2025):</b> A curated collection of 96 official Uzbek "
        "school textbooks (grades 5–11) used to benchmark classification and retrieval "
        "tasks. Libris AI was tested on one textbook from this domain.",
        "<b>CC100-Uzbek:</b> A massive 155M-word corpus used for pre-training models to "
        "understand general Uzbek sentence structure.",
        "<b>MKQA (Multilingual Knowledge Questions and Answers):</b> An open-domain "
        "evaluation set that includes Uzbek, used to test how well AI can answer "
        "questions across different languages.",
    ])]

    s += [h2("C. Methods & Results")]
    s += [p("Recent experiments in 2025 show that <b>Hybrid Search</b> (combining Vector "
            "Similarity with traditional Keyword BM25 search) yields the best results for "
            "academic texts. In studies focusing on Uzbek educational content, fine-tuned "
            "Transformer models achieved an <b>85.2% F1-score</b>, a 15% improvement over "
            "generic multilingual baselines. Libris AI implements this exact hybrid "
            "approach (BM25 + FAISS with RRF), aligning with the current state of the art.")]

    s += [PageBreak()]

    # ── 7. Broader AI Field ───────────────────────────────────────────────────
    s += [Paragraph("Libris AI — Academic Textbook Assistant", TITLE_PAGE)]
    s += [h1("9. How Libris AI Fits within the Broader AI Field")]
    s += [p("Libris AI is situated at the intersection of <b>Information Retrieval (IR)</b> "
            "and <b>Generative AI</b>. It specifically addresses the "
            "\"Long-Tail Language Problem\" in AI.")]
    s += [p("While the \"broad AI field\" is dominated by English-centric models, Libris AI "
            "utilizes <b>Cross-Lingual Information Retrieval (CLIR)</b>. By choosing RAG "
            "as the primary technique, the project moves away from the \"Black Box\" nature "
            "of standard chatbots and toward <b>Verifiable AI</b>. This fits into the 2026 "
            "trend of <b>Domain-Specific AI</b>, where general-purpose models are replaced "
            "by specialized tools that are grounded in authoritative, static data "
            "(the textbook).")]

    s += [h1("10. Future Improvements")]
    s += [bullet([
        "<b>Uzbek Morphological Stemmer:</b> Strip common suffixes ('-ning', '-ga', "
        "'-da', '-ligi', '-lar') before BM25 indexing to match word variants to the "
        "same root token.",
        "<b>Fine-tuned Uzbek Embedding Model:</b> Replace the generic multilingual MiniLM "
        "with a model fine-tuned on Uzbek textbook data for better semantic clustering "
        "of domain-specific terms.",
        "<b>Multi-Turn Conversation Memory:</b> Pass the last 3 conversation turns as "
        "context to the LLM, enabling natural follow-up questions.",
        "<b>Larger Local LLM:</b> Upgrade to qwen2.5:14b or qwen2.5:32b for "
        "grammatically superior Uzbek output.",
        "<b>OCR for Scanned Textbooks:</b> Integrate Tesseract OCR (uzb / uzb_cyrl "
        "language packs) as a fallback for image-based PDFs.",
        "<b>Telegram Bot (aiogram):</b> Deploy as a Telegram bot so students can "
        "access Libris AI from any device without installation.",
        "<b>Cross-Encoder Reranker:</b> Add a cross-encoder reranking step after RRF "
        "to eliminate low-relevance chunks before they enter the LLM context window.",
        "<b>Evaluation Dataset:</b> Build a curated set of 50–100 Uzbek Q&A pairs with "
        "known correct chunk indices to automate Recall@6 measurement.",
    ])]

    # ── Summary ───────────────────────────────────────────────────────────────
    s += [h1("Summary")]
    s += [p("The selected approach — RAG with hybrid BM25 + FAISS retrieval and a locally "
            "hosted LLM — fits the broader AI field's transition toward "
            "<b>Explainable AI (XAI)</b>. By grounding every answer in retrieved textbook "
            "passages and citing source chunks, Libris AI ensures that the "
            "\"Textbook Assistant\" remains a genuine educational tool rather than a "
            "shortcut for academic dishonesty. The system is fully offline, "
            "language-aware, and designed to be extended as better Uzbek NLP resources "
            "become available.")]

    # ── References ────────────────────────────────────────────────────────────
    s += [h1("References")]
    s += [h2("Project Repository")]
    s += [bullet([
        "<b>Libris AI — Source Code:</b> github.com/elchintoyirov/librisai",
    ])]
    s += [h2("Core RAG Frameworks")]
    s += [bullet([
        "<b>LangChain (RAG Guide):</b> python.langchain.com/docs/tutorials/rag/",
        "<b>LlamaIndex (Concepts):</b> docs.llamaindex.ai/en/stable/getting_started/concepts/",
    ])]
    s += [h2("Vector Databases & Search")]
    s += [bullet([
        "<b>FAISS (Facebook AI):</b> github.com/facebookresearch/faiss",
        "<b>Pinecone (RAG Learn):</b> pinecone.io/learn/retrieval-augmented-generation/",
        "<b>Weaviate (RAG Blog):</b> weaviate.io/blog/what-is-rag",
    ])]
    s += [h2("Uzbek Language Resources")]
    s += [bullet([
        "<b>BERTbek / UzBERT:</b> Kuriyozov et al., 2025 — Uzbek Monolingual BERT Models",
        "<b>CC100-Uzbek Corpus:</b> 155M-word Uzbek pre-training corpus",
        "<b>MKQA Dataset:</b> Multilingual Knowledge Questions and Answers (includes Uzbek)",
        "<b>UzTextbooks Dataset (2025):</b> 96 official Uzbek school textbooks (grades 5–11)",
    ])]
    s += [h2("Models & Tools Used")]
    s += [bullet([
        "<b>sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2</b> — HuggingFace",
        "<b>qwen2.5:7b</b> — Alibaba Cloud, served via Ollama (ollama.com)",
        "<b>Docling</b> — IBM Research PDF extraction library",
        "<b>pdfminer.six</b> — Python PDF text extraction",
        "<b>rank-bm25</b> — Python BM25 implementation by D. Larson",
    ])]

    return s


# ── Page footer ───────────────────────────────────────────────────────────────
def on_page(canvas, doc):
    canvas.saveState()
    canvas.setFillColor(GRAY)
    canvas.setFont("Times-Roman", 9)
    canvas.drawCentredString(A4[0]/2, 1.2*cm, str(doc.page))
    canvas.restoreState()


# ── Build ─────────────────────────────────────────────────────────────────────
def build():
    doc = SimpleDocTemplate(
        OUTPUT,
        pagesize=A4,
        leftMargin=3*cm, rightMargin=2.5*cm,
        topMargin=2*cm,  bottomMargin=2*cm,
    )
    story = cover_page() + content()
    doc.build(story, onFirstPage=on_page, onLaterPages=on_page)
    print(f"Generated: {OUTPUT}")


if __name__ == "__main__":
    build()
