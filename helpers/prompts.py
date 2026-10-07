"""Układ wiadomości przekazywanej modelowi (ang. prompt). Gotowy plik: nie edytujesz go."""

from __future__ import annotations

from langchain_core.documents import Document


def build_prompt(system: str, context: list[Document], question: str) -> str:
    """Prompt, który copilot wysyła do LLM-a: tekst systemowy, kontekst i pytanie.

    Każdy blok kontekstu zaczyna się od identyfikatora dokumentu, np. [POL-001], dzięki czemu
    model może wskazać dokumenty, do których prompt systemowy każe mu się odwołać.
    Miniprojekt 1 liczy tokeny tego promptu i w kroku 6 wysyła go raz.
    """
    blocks = [f"[{doc.metadata['doc_id']}]\n{doc.page_content}" for doc in context]
    body = "\n\n---\n\n".join(blocks)
    return f"{system.strip()}\n\n# Kontekst\n\n{body}\n\n# Pytanie\n\n{question.strip()}"
