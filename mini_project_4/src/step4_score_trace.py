"""KROK 4: Oceń, co agent zrobił, a nie tylko, co powiedział

CEL
    Odpowiedź agenta może być trafna z niewłaściwego powodu (właściwa kwota z warunków
    innego dostawcy) albo błędna, choć dobrze brzmi. Dlatego oceniaj ZAPIS PRZEBIEGU (ang. trace),
    test po teście, a każdy test nosi nazwę tego, co naprawdę mierzy. Żaden pojedynczy test nie
    dowodzi, że odpowiedź jest poprawna; razem pokazują, gdzie szukać problemu.

WYNIK
    score_trace(trace, gold) zwraca słownik:

        {"outcome": "answered",              # status przebiegu: answered / error / limit
         "tool_coverage": 1.0,               # odsetek gold.needs spełnionych przez udane wywołania
         "arguments_correct": True,          # każde obliczenie użyło właściwych, pobranych danych
         "answer_fact_coverage": 1.0,        # odsetek gold.key_facts obecnych w odpowiedzi
         "numeric_source_coverage": 1.0,     # odsetek liczb z odpowiedzi popartych zdarzeniem źródłowym
         "uncovered_numbers": [],            # te liczby, w zapisie z odpowiedzi
         "user_stated_numbers": [],          # liczby podane przez użytkownika w pytaniu
         "approval_claim": False,            # czy odpowiedź twierdzi, że coś zatwierdzono?
         "tool_calls": 4, "failed_calls": 0}

WYMAGANIA (sprawdzają je testy)
    Dowodem są tylko udane wywołania: zdarzenia ze statusem "ok" i wynikiem typu dict.
    tool_coverage: odsetek spełnionych gold.needs; None, jeśli nie ma żadnych. Wymaganie (ang. need)
      jest sprawdzane na podstawie udanych zdarzeń need.tool (przy need.supplier_id: tylko te, których wynik
      ma ten supplier_id) ŁĄCZNIE, więc osobne wywołania się sumują (lipiec, potem sierpień,
      potem wrzesień):
      - need.months: każdy miesiąc ma w nich dane (OTIF: w observations; faktura: month
        wyniku, z invoiced_grosze różnym od None);
      - need.missing: każdy miesiąc został ZGŁOSZONY jako brakujący (w missing_months
        któregoś wyniku): to dowód, że „nie ma danych”, którego wywołanie dla innego
        miesiąca nie daje;
      - need.doc_id: fragment z tego dokumentu;
      i istnieje co najmniej jedno takie zdarzenie. Wymaganie z any_of opisuje alternatywne
      ścieżki, np. OTIF za lipiec z danych ALBO z notatek ze spotkania, które go podają.
      Jest spełnione, gdy spełniona jest którakolwiek z alternatyw.
    arguments_correct: None, jeśli nie ma udanego zdarzenia calculate_otif_penalty, którego
      wynik ma status "ok". W przeciwnym razie True tylko wtedy, gdy argumenty KAŻDEGO takiego
      zdarzenia są równe jednemu z gold.calculations (liczby równe z dokładnością do 1e-9)
      ORAZ to wzorcowe obliczenie jest poparte udanymi zdarzeniami danych w tym przebiegu:
      obserwacją OTIF jego dostawcy i miesiąca z tym otif_pct; warunkami umowy jego dostawcy
      z tym celem, stawką i limitem; fakturą jego dostawcy i miesiąca z tym invoice_grosze.
      Obliczenie spoza wzorca (np. dane Aqua z warunkami Mlecznej) jest błędne, nawet jeśli
      arytmetyka się zgadza.
    answer_fact_coverage: odsetek gold.key_facts znalezionych w odpowiedzi; każdy fakt to lista
      alternatyw dopasowywanych przez helpers.quantities.mentions; None, jeśli nie ma kluczowych
      faktów; 0.0, gdy nie ma odpowiedzi (nieudana odpowiedź nadal jest uwzględniana w mianowniku).
    Liczby (helpers.quantities): liczby z odpowiedzi to numbers_in(answer). Liczba jest
      - poparta (covered), jeśli same_quantity() zachodzi dla jakiejś wartości
        z evidence_values(event.tool, event.result) udanego zdarzenia, którego origin to "data"
        albo "calculation". evidence_values czyta tylko to, co narzędzie pobrało albo
        obliczyło: nigdy zapytania, żądanych miesięcy, powtórzonych danych wejściowych
        kalkulatora ani komunikatu (jeden znany wyjątek, w funkcji pomocniczej: uzasadnienia
        sprawdzenia polityki powtarzają podany rabat). "worker_summary" NIGDY nie jest źródłem:
        tekst wygenerowany przez specjalistę nie może poprzeć własnych liczb;
      - w przeciwnym razie podana przez użytkownika (user-stated), jeśli jest równa liczbie
        z pytania (zgłaszana, ale nie jest dowodem);
      - w przeciwnym razie niepoparta (uncovered).
      numeric_source_coverage = covered / (covered + uncovered); None, jeśli obie wartości to 0.
      uncovered_numbers i user_stated_numbers podają Quantity.text w kolejności z odpowiedzi.
    approval_claim: True, jeśli odpowiedź zawiera którąś z gold.approval_claim_phrases (test
      sformułowań, a nie gwarancja); False, gdy nie ma odpowiedzi.
    tool_calls: wszystkie zdarzenia; failed_calls: zdarzenia ze statusem "error".

ZALECANE NARZĘDZIA
    helpers.quantities: mentions, numbers_in, same_quantity;
    helpers.agent_trace: SOURCE_ORIGINS, evidence_values; math.isclose. Przykłady: „Przybornik”
    w mini_project_4/README.md.

NA KONIEC SPRAWDŹ KOD POLECENIEM
    uv run pytest mini_project_4/tests/test_step4_score_trace.py -v
"""

import math

from helpers.agent_trace import SOURCE_ORIGINS, AgentGold, Need, Trace, evidence_values
from helpers.quantities import mentions, numbers_in, same_quantity


def score_trace(trace: Trace, gold: AgentGold) -> dict:
    # TODO: twój kod – zobacz CEL, WYNIK i WYMAGANIA na początku pliku
    raise NotImplementedError("TODO: score_trace")
