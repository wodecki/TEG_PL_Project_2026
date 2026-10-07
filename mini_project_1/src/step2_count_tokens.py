"""KROK 2: Policz tokeny i oszacuj koszt

CEL
    Policz jednostki tekstu przetwarzane przez duży model językowy (LLM), czyli
    tokeny, i na tej podstawie oszacuj miesięczny koszt działania asystenta.

WYNIK
    Dwie funkcje:

        count_tokens(text, config)                -> int
        count_tokens("Witaj, świecie!", config)   -> 5

        monthly_cost(input_tokens_per_question, config)   -> float, USD miesięcznie
        monthly_cost(1000, config)                        -> 19.53

    (19,53 USD = 400 pytań dziennie × 21 dni × (1000 tokenów wejściowych × 0,75 USD
     + 350 tokenów wyjściowych × 4,50 USD) / 1 000 000)

WYMAGANIA (sprawdzają je testy)
    - count_tokens używa narzędzia do podziału tekstu na tokeny (ang. tokenizer), wskazanego w config.get("tokenizer.encoding").
      Pusty napis ma 0 tokenów.
    - monthly_cost bierze wszystkie pozostałe wartości z konfiguracji:
        ceny:       config.get("cost.prices_per_1m_tokens")[config.get("cost.reference_model")]
                    -> {"input": ..., "output": ...}, w USD za 1 000 000 tokenów
        scenariusz: config.get("cost.scenario")
                    -> questions_per_day, working_days_per_month, output_tokens_per_answer
    - Nie zaokrąglaj.

ZALECANE NARZĘDZIA
    tiktoken (tokenizer OpenAI). Przykłady: „Przybornik” w mini_project_1/README.md.

NA KONIEC SPRAWDŹ KOD POLECENIEM
    uv run pytest mini_project_1/tests/test_step2_count_tokens.py -v
"""

import tiktoken

from helpers.config import Config


def count_tokens(text: str, config: Config) -> int:
    # TODO: twój kod – zobacz CEL, WYNIK i WYMAGANIA na początku pliku
    raise NotImplementedError("TODO: count_tokens")


def monthly_cost(input_tokens_per_question: float, config: Config) -> float:
    # TODO: twój kod – zobacz CEL, WYNIK i WYMAGANIA na początku pliku
    raise NotImplementedError("TODO: monthly_cost")
