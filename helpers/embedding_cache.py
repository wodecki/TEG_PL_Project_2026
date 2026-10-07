"""Funkcje pomocnicze do pamięci podręcznej (ang. cache) reprezentacji wektorowych tekstu (ang. embeddings). Gotowy plik: nie edytujesz go."""

from __future__ import annotations

import hashlib
import os

from langchain_classic.storage import LocalFileStore
from langchain_core.embeddings import Embeddings

from helpers.config import Config, MissingConfigError


class CacheOnlyEmbeddings(Embeddings):
    """Zastępuje OpenAI, gdy nie ma OPENAI_API_KEY: każdy tekst musi pochodzić z cache.

    Sam nigdy nie tworzy wektora. Jeśli trafia do niego jakiś tekst, to znaczy, że brakuje go
    w kursowym cache: wtedy kończy pracę błędem, który wskazuje ten tekst.
    """

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        raise MissingConfigError(
            f"Liczba tekstów spoza kursowego cache embeddingów: {len(texts)}, np. {texts[0][:60]!r}. "
            "Do ich embeddingu potrzebny jest OPENAI_API_KEY w .env. W Miniprojekcie 1 każdy poprawny "
            "chunk jest w cache, więc brak zwykle oznacza, że chunki różnią się od ustalonego podziału (krok 3)."
        )

    def embed_query(self, text: str) -> list[float]:
        raise MissingConfigError(
            f"Tego pytania nie ma w kursowym cache embeddingów: {text[:60]!r}. "
            "Do embeddingu nowych pytań potrzebny jest OPENAI_API_KEY w .env."
        )


def underlying_embeddings() -> Embeddings | None:
    """To, co build_embeddings(config, underlying=...) ma opakować.

    None (wtedy build_embeddings używa OpenAI), gdy OPENAI_API_KEY jest ustawiony; w przeciwnym
    razie model korzystający tylko z cache, więc z OpenRouterem lub Ollamą Miniprojekt 1
    działa bez klucza OpenAI.
    """
    return None if os.environ.get("OPENAI_API_KEY") else CacheOnlyEmbeddings()


def require_openai_key(reason: str) -> None:
    """Kończy pracę czytelnym błędem, jeśli OPENAI_API_KEY nie jest ustawiony."""
    if not os.environ.get("OPENAI_API_KEY"):
        raise MissingConfigError(f"OPENAI_API_KEY nie jest ustawiony: {reason} Skopiuj .env.example do .env i wpisz swój klucz.")


def missing_from_cache(config: Config, texts: list[str]) -> list[int]:
    """Pozycje tekstów, których wektorów NIE MA w kursowym cache.

    Czyta folder cache bezpośrednio (klucz = nazwa modelu + sha256 tekstu), więc działa
    bez twojego kroku 4 i nie wywołuje API.
    """
    model = config.get("embeddings.model")
    store = LocalFileStore(str(config.path("paths.embedding_cache")))
    keys = [model + hashlib.sha256(text.encode("utf-8")).hexdigest() for text in texts]
    return [i for i, vector in enumerate(store.mget(keys)) if vector is None]


def live_query_embeddings(config: Config) -> Embeddings:
    """Embeddingi TWOICH pytań liczone na bieżąco przez OpenAI, bez zapisu do kursowego cache.

    Dla try_search.py i ask.py: wektory dokumentów pochodzą z cache, a twoje pytania są
    zamieniane na embeddingi na bieżąco (potrzebny OPENAI_API_KEY) i nigdy nie są zapisywane.
    """
    from langchain_openai import OpenAIEmbeddings

    return OpenAIEmbeddings(model=config.get("embeddings.model"))
