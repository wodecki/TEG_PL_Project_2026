r"""KROK 3: Oceń rekord przebiegu w sposób deterministyczny

CEL
    Zmierz odpowiedź bez drugiego LLM-a: ile potrzebnych dowodów zawiera znaleziony
    tekst, czy odpowiedź podaje wymagane fakty i czy odwołania do źródeł są obecne,
    prawidłowe i trafne. Ustal też, co się stało: odpowiedź, odmowa czy błąd.

    Są to niedrogie, przybliżone miary. Dopasowanie fraz nie rozumie znaczenia: może przeoczyć
    dowód sformułowany innymi słowami i zaakceptować właściwe słowa w złym miejscu.
    Traktuj te liczby jako sygnały do sprawdzenia, a nie jako werdykty.

WYNIK
    score_record(record, gold) zwraca słownik:

        {"outcome": "refused",               # "answered" | "refused" | "error"
         "evidence_phrase_coverage": 0.0,    # udział gold.evidence_facts znalezionych w tekstach kontekstu
         "answer_coverage": None,            # udział gold.key_facts znalezionych w odpowiedzi
         "citations_present": None, "citations_valid": None, "cites_relevant": None,
         "refusal": "phrases_missing"}       # opis niżej

    (prawdziwy wynik: rekord M03 „Co SUP-114 mówi o karach?” z przebiegu
    referencyjnego. Wyszukiwanie zwróciło trzy chunki umowy z innym dostawcą
    (CON-102), a model odmówił odpowiedzi. Dla odpowiedzi, np. M05, wszystkie
    pola są wypełnione: "outcome": "answered", oba pokrycia 1.0, trzy razy True,
    "refusal": None.)

WYMAGANIA (sprawdzają je testy)
    Dopasowanie faktu (listy akceptowanych wariantów) do tekstu:
    - bez rozróżniania wielkości liter; każdy ciąg białych znaków liczy się jak
      jedna spacja;
    - wariant pasuje tylko jako cała fraza, nie wewnątrz dłuższego słowa ani
      liczby. „zarząd” nie pasuje do „zarządu” (dlatego wzorzec wymienia odmienione
      formy jako osobne warianty); „9%” nie pasuje do „19%”, „19,9%” ani „1.9%”;
      „500 000 PLN” nie pasuje do „1 500 000 PLN” (cyfry grupowane spacjami),
      a „500,000 PLN” do „1,500,000 PLN”. Zwykła interpunkcja wokół frazy nie
      przeszkadza: „9%.” i „(CFO)” pasują.
    evidence_phrase_coverage: dla pytań, na które korpus odpowiada, udział
      gold.evidence_facts znalezionych w połączonych tekstach kontekstu; None dla
      pytań bez odpowiedzi w korpusie (i dla wzorca bez fraz dowodowych). Opisuje ZNALEZIONY TEKST, więc liczysz go
      przy każdym wyniku, także przy błędzie.
    outcome:
    - "error", jeśli record.error jest ustawiony albo record.output to None. Błąd
      nie dostaje punktów za odpowiedź, odwołania ani odmowę: te pola mają wartość None.
    - "refused", jeśli output.answerable ma wartość False, w przeciwnym razie "answered".
    answer_coverage, citations_present, citations_valid, cites_relevant: tylko dla
      rekordów "answered", w pozostałych None.
      - answer_coverage: udział gold.key_facts znalezionych w output.answer (None,
        jeśli pytanie nie ma kluczowych faktów).
      - citations_present: co najmniej jedno odwołanie.
      - citations_valid: odwołania są obecne ORAZ każde z nich to doc_id z kontekstu.
      - cites_relevant: co najmniej jedno odwołanie jest w gold.relevant_docs.
    refusal:
      - pytanie bez odpowiedzi w korpusie: "correct" przy odmowie, "missed" przy
        odpowiedzi;
      - pytanie z odpowiedzią w korpusie, odmowa: "phrases_missing", gdy
        evidence_phrase_coverage < 1 (najpierw sprawdź wyszukiwanie), w przeciwnym
        razie "phrases_present" (frazy dowodowe były w tekście: prawdopodobnie
        niesłuszna odmowa, ale sprawdź);
      - w pozostałych przypadkach None.

ZALECANE NARZĘDZIA
    Moduł re (re.escape, asercje typu lookaround, np. (?<!\w) i (?!\w)), str.casefold.
    Przy liczbach samo (?<!\w) nie wystarcza: nie sprawdza cyfry przed przecinkiem
    w „19,9%” ani cyfry przed spacją w „1 500 000”. Pierwszy przypadek można
    uwzględnić asercją (?<!\d[.,]), a drugi — (?<!\d ). Zobacz podpowiedź
    do kroku 3 w README. Przykłady: „Przybornik” w mini_project_2/README.md.

NA KONIEC SPRAWDŹ KOD POLECENIEM
    uv run pytest mini_project_2/tests/test_step3_score_record.py -v
"""

import re

from helpers.gold import GoldQuestion
from helpers.records import RunRecord


def score_record(record: RunRecord, gold: GoldQuestion) -> dict:
    # TODO: twój kod – zobacz CEL, WYNIK i WYMAGANIA na początku pliku
    raise NotImplementedError("TODO: score_record")
