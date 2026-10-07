"""KROK 1: Wczytaj dokumenty

CEL
    Zamień korpus Kovalo w obiekty Document z LangChain: jeden na każdy plik
    Markdown w data/corpus/, z jego tekstem i wierszem z data/corpus/catalog.csv.

WYNIK
    load_documents(config) zwraca listę 18 obiektów Document posortowaną według
    doc_id. Przykład: pierwszy z nich wygląda tak:

        Document(
            page_content="# Streszczenie umowy z dostawcą: Mleczna Dolina (SUP-114)\\n\\n## Strony i okres obowiązywania ...",
            metadata={
                "doc_id": "CON-101",
                "title": "Streszczenie umowy z dostawcą: Mleczna Dolina (SUP-114)",
                "doc_type": "contract",
                "department": "Zakupy",
                "owner": "Kierownik działu zakupów",
                "effective_date": "2025-04-01",
                "language": "pl",
                "source": "CON-101_supplier_agreement_mleczna_dolina.md",
            },
        )

WYMAGANIA (sprawdzają je testy)
    - Ścieżki odczytaj z konfiguracji: config.path("paths.corpus_dir") i
      config.path("paths.corpus_catalog").
    - page_content to tekst pliku bez żadnych zmian. Czytaj pliki jako UTF-8:
      dokumenty zawierają polskie litery, np. ą, ę, ł, a domyślne kodowanie w systemie Windows
      może być inne niż UTF-8.
    - metadata zawiera dokładnie pola katalogu wymienione w
      config.get("corpus.required_metadata") oraz "source", czyli nazwę pliku.
    - Jeśli plik nie ma wiersza w katalogu albo wiersz ma puste pole (pusty napis ""),
      zgłoś ValueError z nazwą pliku.

ZALECANE NARZĘDZIA
    DirectoryLoader i TextLoader z LangChain oraz gotowa funkcja load_catalog()
    z helpers.catalog. Przykłady: „Przybornik” w mini_project_1/README.md.

NA KONIEC SPRAWDŹ KOD POLECENIEM
    uv run pytest mini_project_1/tests/test_step1_load_documents.py -v
"""

from pathlib import Path

from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_core.documents import Document

from helpers.catalog import load_catalog
from helpers.config import Config


def load_documents(config: Config) -> list[Document]:
    # TODO: twój kod – zobacz CEL, WYNIK i WYMAGANIA na początku pliku
    raise NotImplementedError("TODO: load_documents")
