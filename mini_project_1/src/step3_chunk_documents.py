"""KROK 3: Podziel dokumenty na fragmenty (ang. chunks)

CEL
    Podziel każdy dokument na mniejsze fragmenty, nazywane chunkami, które można
    przeszukiwać pojedynczo, i nadaj każdemu chunkowi czytelny identyfikator.

WYNIK
    chunk_documents(docs, config) zwraca listę obiektów Document (chunków).
    Przykład: pierwszy chunk CON-101 wygląda tak:

        Document(
            page_content="# Streszczenie umowy z dostawcą: Mleczna Dolina (SUP-114)\\n\\n## Strony i okres obowiązywania ...",
            metadata={
                "doc_id": "CON-101",
                "title": "Streszczenie umowy z dostawcą: Mleczna Dolina (SUP-114)",
                ...                       <- wszystkie metadane jego dokumentu
                "chunk_index": 0,         <- 0, 1, 2, ... w obrębie każdego dokumentu
                "chunk_id": "CON-101#000",
            },
        )

WYMAGANIA (sprawdzają je testy)
    - Użyj ustalonych ustawień i żadnych innych:
        config.get("chunking.chunk_size")      800 znaków
        config.get("chunking.chunk_overlap")   120 znaków
        config.get("chunking.separators")      akapity, wiersze, zdania, słowa
    - Każdy chunk zachowuje metadane swojego dokumentu i dostaje "chunk_index"
      oraz "chunk_id" (doc_id + "#" + numer zapisany trzema cyframi: "POL-001#000",
      "POL-001#001").
    - Zachowaj tekst każdego chunku dokładnie w postaci zwróconej przez narzędzie
      dzielące tekst (ang. splitter).
    - Zachowaj kolejność dokumentów.

ZALECANE NARZĘDZIA
    RecursiveCharacterTextSplitter z LangChain (jego metoda split_documents sama
    kopiuje metadane do chunków). Przykłady: „Przybornik” w mini_project_1/README.md.

NA KONIEC SPRAWDŹ KOD POLECENIEM
    uv run pytest mini_project_1/tests/test_step3_chunk_documents.py -v
"""

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from helpers.config import Config


def chunk_documents(docs: list[Document], config: Config) -> list[Document]:
    # TODO: twój kod – zobacz CEL, WYNIK i WYMAGANIA na początku pliku
    raise NotImplementedError("TODO: chunk_documents")
