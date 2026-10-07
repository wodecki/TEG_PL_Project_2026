"""KROK 2: Odpowiedz na pytanie z odwołaniami do źródeł

CEL
    Połącz wyszukiwanie z generowaniem odpowiedzi. Znajdź najlepiej dopasowane
    fragmenty dokumentów (ang. chunks) i wyślij je
    razem z pytaniem do swojego LLM-a i odbierz odpowiedź w ustalonym schemacie
    (ang. structured output): tekst odpowiedzi, id dokumentów, na których się opiera,
    i informację, czy dokumenty w ogóle odpowiadają na pytanie. Zwróć wszystko jako
    rekord przebiegu (ang. run record), żeby kolejne kroki mogły sprawdzić, co dokładnie
    widział model.

WYNIK
    answer_question(question, vector_store, llm, config) zwraca RunRecord
    (helpers/records.py):

        record.question  -> 'Kto zatwierdza spisanie w straty towaru o wartości powyżej 25 000 PLN?'
        record.context   -> [ContextItem(doc_id='PRO-202', chunk_id='PRO-202#ctx002', text='...'),
                             ContextItem(doc_id='POL-004', chunk_id='POL-004#ctx004', text='...'),
                             ContextItem(doc_id='POL-005', chunk_id='POL-005#ctx000', text='...')]
        record.output    -> Answer(answer='Spisanie w straty towaru o wartości powyżej 25 000 PLN zatwierdza CFO.',
                                   citations=['PRO-202'], answerable=True)
        record.error     -> None

    Jeśli odpowiedzi modelu nie da się odczytać, output ma wartość None, a pole error
    zawiera przyczynę. (pytanie M05 z przebiegu referencyjnego, openai / gpt-5.4-mini;
    odpowiedź twojego LLM-a może brzmieć inaczej)

WYMAGANIA (sprawdzają je testy)
    - Pobierz config.get("retrieval.top_k") chunków funkcją search(vector_store, question, k)
      z Miniprojektu 1.
    - Prompt to helpers.prompts.build_prompt(config.get("prompts.answer_system"),
      <znalezione chunki>, question), więc każdy blok kontekstu zaczyna się od swojego [doc_id].
    - Poproś o structured output z gotowym schematem Answer (helpers/records.py).
    - record.context wymienia znalezione chunki w kolejności wyszukiwania, z doc_id,
      chunk_id i dokładnie tym tekstem, który trafił do promptu.
    - Sprowadź każde odwołanie do samego id dokumentu. Akceptuj dokładnie te formy:
      nawiasy kwadratowe, wielkość liter i spacje ("[PL-601]" -> "PL-601", " pol-001 " ->
      "POL-001") oraz przyrostek chunku z kontekstem ("CON-101#ctx003" -> "CON-101"; inny
      przyrostek, np. "#003", nie pochodzi z tego indeksu i zostaje). Wszystko inne
      zostaje bez zmian (po usunięciu spacji na początku i końcu, wielkimi literami), więc dalej
      jest nieprawidłowe: "CON-1019" NIE może stać się "CON-101". Usuń duplikaty,
      zachowaj kolejność.
    - Nigdy nie zgłaszaj wyjątku z powodu modelu: jeśli wywołanie się nie uda albo nie
      zwróci obiektu Answer, zwróć rekord z output=None i krótkim komunikatem w error.

ZALECANE NARZĘDZIA
    llm.with_structured_output(Answer), search z Miniprojektu 1, build_prompt, wyrażenie
    regularne dla id dokumentów. Przykłady: „Przybornik” w mini_project_2/README.md.

NA KONIEC SPRAWDŹ KOD POLECENIEM
    uv run pytest mini_project_2/tests/test_step2_answer_question.py -v
"""

import re

from langchain_core.language_models import BaseChatModel
from langchain_core.vectorstores import VectorStore

from helpers.config import Config
from helpers.prompts import build_prompt
from helpers.records import Answer, ContextItem, RunRecord
from mini_project_1.src.step5_search import search


def answer_question(question: str, vector_store: VectorStore, llm: BaseChatModel, config: Config) -> RunRecord:
    # TODO: twój kod – zobacz CEL, WYNIK i WYMAGANIA na początku pliku
    raise NotImplementedError("TODO: answer_question")
