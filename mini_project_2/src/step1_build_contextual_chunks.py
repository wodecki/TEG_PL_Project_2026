"""KROK 1: Fragmenty (ang. chunks) z kontekstem dokumentu

CEL
    Dodaj do każdego fragmentu informację o dokumencie źródłowym. W Miniprojekcie 1 chunk umowy z Mleczną Doliną zawierał klauzulę
    o karze umownej, ale w jego tekście nie było ani „SUP-114”, ani „umowa
    z dostawcą”: te informacje znajdowały się poza tym fragmentem. Tutaj każdy chunk
    odpowiada sekcji dokumentu i zaczyna się od „<tytuł dokumentu> > <nagłówek sekcji>”.

WYNIK
    build_contextual_chunks(documents, config) zwraca dokumenty LangChain (Document):

        chunks[3].page_content
        -> 'Streszczenie umowy z dostawcą: Mleczna Dolina (SUP-114) > Kara umowna\n\n## Kara umowna  \nJeśli miesięczny wskaźnik OTIF spadnie poniżej 97%, ...'
        chunks[3].metadata
        -> {..., 'doc_id': 'CON-101', 'section': 'Kara umowna', 'chunk_id': 'CON-101#ctx003'}

    (prawdziwy chunk z korpusu Kovalo: klauzula o karze ma teraz w tekście „SUP-114”)

WYMAGANIA (sprawdzają je testy)
    - Najpierw podziel każdy dokument według nagłówków Markdown (# i ##),
      zostawiając nagłówki w tekście. Potem podziel długie sekcje z ustawieniami
      podziału z konfiguracji („chunking.chunk_size”, „chunking.chunk_overlap”,
      „chunking.separators”).
    - page_content = "<title> > <section>" + pusty wiersz + tekst sekcji, gdzie
      <title> to metadata["title"], a <section> to nagłówek ##. Część bez
      nagłówka ## zaczyna się od samego "<title>".
    - metadata zachowuje wszystkie pola dokumentu i dostaje dwa nowe: "section"
      (nagłówek ## albo "") oraz "chunk_id" = "<doc_id>#ctx<numer>". Numeracja
      zaczyna się od ctx000 w każdym dokumencie (3 cyfry).
    - Każdy chunk musi dokładnie odpowiadać dołączonej pamięci podręcznej (ang. cache), tak jak
      w Miniprojekcie 1.

ZALECANE NARZĘDZIA
    MarkdownHeaderTextSplitter i RecursiveCharacterTextSplitter z LangChain.
    Przykłady: „Przybornik” w mini_project_2/README.md.

NA KONIEC SPRAWDŹ KOD POLECENIEM
    uv run pytest mini_project_2/tests/test_step1_build_contextual_chunks.py -v
"""

from langchain_core.documents import Document
from langchain_text_splitters import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter

from helpers.config import Config


def build_contextual_chunks(documents: list[Document], config: Config) -> list[Document]:
    # TODO: twój kod – zobacz CEL, WYNIK i WYMAGANIA na początku pliku
    raise NotImplementedError("TODO: build_contextual_chunks")
