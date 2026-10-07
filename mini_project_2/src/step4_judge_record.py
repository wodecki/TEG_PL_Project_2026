"""KROK 4: Oceń rekord przebiegu za pomocą modelu oceniającego

CEL
    Dopasowanie kluczowych faktów nie odróżni „zatwierdza CFO” od „nie CFO”.
    Przygotuj prostego sędziego, czyli model oceniający (ang. LLM-as-judge): podaj mu pytanie, dokładnie ten kontekst,
    który widział model, odpowiedź i odpowiedź wzorcową, a odbierz werdykt
    w ustalonym schemacie. Kryteria oceny (rubrykę) projektujesz samodzielnie:
    co się liczy jako poprawne, a co jako oparte na źródłach (ang. grounded).

WYNIK
    judge_record(record, gold, llm) zwraca słownik:

        {"correct": True, "grounded": True,
         "reason": "Odpowiedź dokładnie odpowiada odpowiedzi wzorcowej: wskazuje CFO jako osobę ...",
         "error": None}

    Ocenia tylko rekordy z odpowiedzią; dla odmów i nieudanych rekordów zwraca
    {"correct": None, "grounded": None, "reason": None, "error": None} bez wywołania
    LLM-a. (werdykt dla M05 z przebiegu referencyjnego, openai / gpt-5.4-mini)

WYMAGANIA (sprawdzają je testy)
    - Użyj odpowiedzi w ustalonym schemacie (ang. structured output) z gotowym schematem Verdict (helpers/records.py).
    - Wywołuj LLM tylko dla rekordów, których output odpowiada (answerable=True).
    - Prompt sędziego zawiera pytanie, każdy tekst kontekstu z rekordu (ZAPISANY
      kontekst, nie nowe wyszukiwanie), odpowiedź i gold.reference.
    - Nigdy nie zgłaszaj wyjątku z powodu modelu: jeśli werdyktu sędziego nie da się
      odczytać, zwróć te same klucze, a w error krótki komunikat.

ZALECANE NARZĘDZIA
    llm.with_structured_output(Verdict). Przykłady: „Przybornik” w mini_project_2/README.md.

NA KONIEC SPRAWDŹ KOD POLECENIEM
    uv run pytest mini_project_2/tests/test_step4_judge_record.py -v
"""

from langchain_core.language_models import BaseChatModel

from helpers.gold import GoldQuestion
from helpers.records import RunRecord, Verdict


def judge_record(record: RunRecord, gold: GoldQuestion, llm: BaseChatModel) -> dict:
    # TODO: twój kod – zobacz CEL, WYNIK i WYMAGANIA na początku pliku
    raise NotImplementedError("TODO: judge_record")
