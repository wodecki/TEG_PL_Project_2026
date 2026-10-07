"""KROK 4: Model reprezentacji wektorowych (ang. embeddings) z pamięcią podręczną (ang. cache)

CEL
    Utwórz model, który zamienia tekst w wektory (OpenAI text-embedding-3-small),
    i dodaj obsługę pamięci podręcznej: każdy tekst jest najpierw wyszukiwany w cache,
    a do API trafiają tylko teksty, których tam brakuje.

    Kurs dostarcza gotowy cache (data/embeddings/cache/) z wektorami każdego
    fragmentu dokumentu (ang. chunk) zgodnego z ustawieniami kursu i każdego pytania testowego, więc Miniprojekt 1 nie wykonuje
    żadnych płatnych wywołań API.

WYNIK
    build_embeddings(config) zwraca model embeddingów z LangChain:

        embeddings = build_embeddings(config)
        embeddings.embed_query("Jak liczy się OTIF?")       -> [-0.043, 0.027, ...]  (1536 liczb)
        embeddings.embed_documents([text1, text2])          -> [[...], [...]]

WYMAGANIA (sprawdzają je testy)
    - Model to config.get("embeddings.model").
    - Cache znajduje się w folderze config.path("paths.embedding_cache").
    - Do pamięci podręcznej trafiają zarówno dokumenty, JAK I pytania.
    - Klucze cache muszą się zgadzać z cache kursu: namespace = nazwa modelu,
      key encoder = "sha256".
    - build_embeddings(config, underlying=some_model) opakowuje `some_model`
      zamiast modelu OpenAI. Dzięki temu testy działają bez klucza API.
    Przy samodzielnym uruchamianiu: samo build_embeddings(config) korzysta z OpenAI i potrzebuje
    OPENAI_API_KEY, więc bez klucza pojawi się błąd OpenAI, który nie wynika z błędu
    w twoim kodzie. Gotowe programy przekazują
    underlying=helpers.embedding_cache.underlying_embeddings() (teksty z cache nie
    wymagają klucza).

ZALECANE NARZĘDZIA
    OpenAIEmbeddings, CacheBackedEmbeddings i LocalFileStore z LangChain.
    Przykłady: „Przybornik” w mini_project_1/README.md.

NA KONIEC SPRAWDŹ KOD POLECENIEM
    uv run pytest mini_project_1/tests/test_step4_build_embeddings.py -v
"""

from langchain_classic.embeddings import CacheBackedEmbeddings
from langchain_classic.storage import LocalFileStore
from langchain_core.embeddings import Embeddings
from langchain_openai import OpenAIEmbeddings

from helpers.config import Config


def build_embeddings(config: Config, underlying: Embeddings | None = None) -> Embeddings:
    # TODO: twój kod – zobacz CEL, WYNIK i WYMAGANIA na początku pliku
    raise NotImplementedError("TODO: build_embeddings")
