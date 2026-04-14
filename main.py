"""
main.py — Libris AI console chat application.

Run:
    python main.py
"""

import sys
import textwrap
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# ── Width helpers ─────────────────────────────────────────────────────────────

WIDTH = 70


def hr(char: str = "─") -> str:
    return char * WIDTH


def banner() -> None:
    print()
    print("╔" + "═" * (WIDTH - 2) + "╗")
    title = "LIBRIS AI"
    subtitle = "Chat with your textbooks"
    print("║" + title.center(WIDTH - 2) + "║")
    print("║" + subtitle.center(WIDTH - 2) + "║")
    print("╚" + "═" * (WIDTH - 2) + "╝")
    print()


def print_help() -> None:
    print(hr())
    print("Commands:")
    print("  /books    — list all indexed books")
    print("  /add      — ingest a new PDF")
    print("  /switch   — switch to a different book")
    print("  /clear    — clear the current conversation history")
    print("  /help     — show this message")
    print("  /quit     — exit Libris AI")
    print(hr())


def wrap(text: str, prefix: str = "") -> None:
    """Word-wrap text and print it."""
    lines = text.splitlines()
    for line in lines:
        if line.strip() == "":
            print()
            continue
        for wrapped in textwrap.wrap(line, width=WIDTH - len(prefix)) or [""]:
            print(prefix + wrapped)


# ── Book helpers ──────────────────────────────────────────────────────────────

def list_books_display() -> list[dict]:
    from libris.store import list_books
    books = list_books()
    if not books:
        print("  (no books indexed yet — use /add to ingest a PDF)")
        return []
    for i, book in enumerate(books, 1):
        print(f"  [{i}] {book['name']}  "
              f"({book['num_pages']} pages, {book['num_chunks']} chunks)  "
              f"id={book['id']}")
    return books


def prompt_add_book() -> dict | None:
    """Ask for a PDF path, ingest it, return the metadata dict or None."""
    from libris.store import ingest_book

    path_str = input("  PDF path: ").strip().strip('"').strip("'")
    if not path_str:
        print("  Cancelled.")
        return None

    pdf_path = Path(path_str)
    if not pdf_path.exists():
        print(f"  File not found: {pdf_path}")
        return None

    print()
    print(f"  Ingesting '{pdf_path.name}' — this may take a minute …")
    print()
    try:
        book = ingest_book(pdf_path)
        print()
        print(f"  Done! '{book['name']}' is ready.")
        return book
    except Exception as exc:
        print(f"  Ingestion failed: {exc}")
        return None


def select_book(books: list[dict]) -> dict | None:
    """Let the user pick a book by number; return its metadata or None."""
    if not books:
        return None
    while True:
        choice = input("  Choose a book number (or Enter to cancel): ").strip()
        if choice == "":
            return None
        if choice.isdigit() and 1 <= int(choice) <= len(books):
            return books[int(choice) - 1]
        print(f"  Please enter a number between 1 and {len(books)}.")


# ── RAG session ───────────────────────────────────────────────────────────────

def load_retriever_for_book(book: dict):
    """Load and return the FAISS retriever for the given book."""
    from libris.retriever import load_retriever

    print(f"  Loading index for '{book['name']}' …", end="", flush=True)
    retriever = load_retriever(book["index_path"])
    print(" ready.")
    return retriever


def chat_loop(book: dict, retriever) -> str:
    """
    Run the interactive chat loop for a single book.

    Returns "switch" or "quit" to signal what to do next.
    """
    history: list[tuple[str, str]] = []   # (question, answer) pairs

    print()
    print(hr())
    print(f"  Chatting with: {book['name']}")
    print("  Type /help for commands, or just ask a question.")
    print(hr())
    print()

    while True:
        try:
            user_input = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return "quit"

        if not user_input:
            continue

        # ── Commands ──────────────────────────────────────────────────────────
        if user_input.startswith("/"):
            cmd = user_input.lower().split()[0]

            if cmd == "/quit":
                return "quit"

            if cmd == "/switch":
                return "switch"

            if cmd == "/books":
                print(hr())
                list_books_display()
                print(hr())
                continue

            if cmd == "/clear":
                history.clear()
                print("  Conversation history cleared.")
                continue

            if cmd == "/help":
                print_help()
                continue

            if cmd == "/add":
                print(hr())
                new_book = prompt_add_book()
                print(hr())
                if new_book:
                    answer = input(
                        f"  Switch to '{new_book['name']}' now? [y/N]: "
                    ).strip().lower()
                    if answer == "y":
                        # Return to main loop so the new book is loaded
                        return "switch_to:" + new_book["id"]
                continue

            print(f"  Unknown command '{cmd}'. Type /help for help.")
            continue

        # ── RAG query ─────────────────────────────────────────────────────────
        from libris.llm import ask

        print()
        print("Libris: ", end="", flush=True)
        try:
            answer, source_docs = ask(user_input, retriever)
        except Exception as exc:
            print(f"\n  Error: {exc}")
            print()
            continue

        # Show sources
        if source_docs:
            sources = {
                f"chunk {d.metadata.get('chunk_index', '?')}"
                for d in source_docs
            }
            print(f"  [sources: {', '.join(sorted(sources))}]")

        print()
        history.append((user_input, answer))


# ── Entry point ───────────────────────────────────────────────────────────────

def main() -> None:
    # Validate Ollama is reachable
    import urllib.request
    try:
        urllib.request.urlopen("http://localhost:11434", timeout=2)
    except Exception:
        print("Error: Ollama is not running.")
        print("Start it with:  ollama serve")
        print("Or download from https://ollama.com/download")
        sys.exit(1)

    banner()
    print_help()
    print()

    active_book: dict | None = None
    active_retriever = None

    while True:
        # ── Book selection ────────────────────────────────────────────────────
        if active_book is None:
            print(hr())
            print("Indexed books:")
            books = list_books_display()
            print(hr())
            print()

            if books:
                print("Select a book to chat with, or /add to ingest a new PDF.")
                choice = input("> ").strip()

                if choice.lower() in ("/quit", "quit"):
                    break

                if choice.lower() == "/add":
                    print(hr())
                    new_book = prompt_add_book()
                    print(hr())
                    if new_book:
                        active_book = new_book
                else:
                    # Try to interpret as a number
                    books = list_books_display() if not books else books
                    if choice.isdigit() and 1 <= int(choice) <= len(books):
                        active_book = books[int(choice) - 1]
                    else:
                        print("  Please enter a book number or /add.")
                        continue
            else:
                print("No books indexed yet.")
                ans = input("  Ingest a PDF now? [Y/n]: ").strip().lower()
                if ans in ("", "y"):
                    print(hr())
                    new_book = prompt_add_book()
                    print(hr())
                    if new_book:
                        active_book = new_book
                    else:
                        continue
                else:
                    break

            if active_book is None:
                continue

            # Load retriever for the selected book
            print()
            try:
                active_retriever = load_retriever_for_book(active_book)
            except Exception as exc:
                print(f"  Failed to load index: {exc}")
                active_book = None
                continue

        # ── Chat ──────────────────────────────────────────────────────────────
        signal = chat_loop(active_book, active_retriever)

        if signal == "quit":
            break

        if signal == "switch":
            active_book = None
            active_retriever = None
            print()
            continue

        if signal.startswith("switch_to:"):
            from libris.store import get_book
            target_id = signal.split(":", 1)[1]
            target = get_book(target_id)
            if target:
                active_book = None   # force re-load via main loop
                active_retriever = None
            continue

    print()
    print("Goodbye! Happy studying.")
    print()


if __name__ == "__main__":
    main()
