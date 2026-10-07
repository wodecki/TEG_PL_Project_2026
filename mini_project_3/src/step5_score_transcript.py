"""KROK 5: Ocena zapisu rozmowy, etap po etapie

CEL
    Błędy mogą wystąpić na różnych etapach przepływu pracy (ang. workflow): LLM źle odczyta wiadomość, stan
    wniosku zostanie źle zaktualizowany, polityka wskaże złe role, graf zatrzyma się
    bez potrzeby albo skończy w złym statusie. Oceń każdy etap osobno, na podstawie
    odpowiedzi wzorcowych sprawdzonych ręcznie – nigdy na podstawie własnego silnika
    reguł, który mógłby popełnić ten sam błąd po obu stronach porównania.

WYNIK
    score_transcript(turns, gold) zwraca słownik par [trafne, ocenione]:

        {"route": [12, 13], "fields": [10, 13], "request": [7, 8], "approvers": [9, 9],
         "pauses": [12, 13], "status": [12, 13], "errors": 1, "details": [...]}

    (przykładowe liczby, niezwiązane z przebiegiem referencyjnym)

WYMAGANIA (sprawdzają je testy)
    turns: wpisy zapisu rozmowy z helpers.workflow.run_turn (w kolejności); gold:
    odpowiadające im słowniki "expect" z data/eval/mini_project_3_dialogues.yaml,
    w tej samej kolejności. Różne długości -> ValueError (każde porównanie byłoby
    przesunięte).
    Słownik wzorca może zawierać: kind, fields (słownik pól Turn), request (słownik pól
    DiscountRequest), approvers, pauses, status. Oceniaj wymiar tylko w turach, których
    wzorzec go zawiera, i licz je wszystkie w mianowniku – także tury, w których program
    zawiódł. Każdy wpis zapisu rozmowy to słownik; entry["turn"] to zrozumienie
    wiadomości (słownik albo None, jeśli się nie udało), entry["request"] to wniosek
    (słownik albo None):
    - route: entry["turn"]["kind"] == kind ze wzorca
    - fields: każde wymienione pole jest równe entry["turn"][field]
    - request: każde wymienione pole jest równe entry["request"][field] (brak
      wniosku -> źle)
    - approvers: entry["approvers"], te same role w tej samej kolejności
    - pauses: entry["pauses"], ta sama lista par [type, rola-albo-pole], w tej samej
      kolejności
    - status: entry["status"] równy statusowi ze wzorca
    Liczby są równe, gdy różnią się o mniej niż 0,01. "errors" liczy wpisy, których
    status to "error" albo których kind to "error" (spośród wszystkich tur).
    "details": jeden słownik na turę z wymiarami, które były błędne.

ZALECANE NARZĘDZIA
    Zwykły Python. Przykłady: „Przybornik” w mini_project_3/README.md.

NA KONIEC SPRAWDŹ KOD POLECENIEM
    uv run pytest mini_project_3/tests/test_step5_score_transcript.py -v
"""


def score_transcript(turns: list[dict], gold: list[dict]) -> dict:
    # TODO: twój kod – zobacz CEL, WYNIK i WYMAGANIA na początku pliku
    raise NotImplementedError("TODO: score_transcript")
