"""Uwaga, którą programy wywołujące model wypisują, gdy używasz innego LLM-a niż referencyjny.
Gotowy plik: nie edytujesz go."""

from __future__ import annotations

from helpers.config import Config


def other_llm_note(config: Config) -> str | None:
    """None dla referencyjnego LLM-a; w przeciwnym razie krótka uwaga, że wyniki mogą się różnić."""
    reference = (config.get("reference_llm.provider"), config.get("reference_llm.model"))
    yours = (config.get("llm.provider"), config.get("llm.model"))
    if yours == reference:
        return None
    return (
        f"Uwaga: ten projekt zbudowano i sprawdzono z {reference[0]} / {reference[1]}. "
        f"Używasz {yours[0]} / {yours[1]}, więc odpowiedzi, wyniki i koszty mogą się różnić od "
        "przebiegu referencyjnego z README, a niektóre odpowiedzi mogą się nie udać. Testy i quizy "
        "od tego nie zależą."
    )
