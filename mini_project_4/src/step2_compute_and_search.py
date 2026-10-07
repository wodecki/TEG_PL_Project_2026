"""KROK 2: Kalkulator, sprawdzenie polityki rabatowej i wyszukiwanie w dokumentach

CEL
    Trzy kolejne narzędzia. Kalkulator liczy karę umowną dokładnie i pokazuje każdą wartość
    pośrednią, więc każdą kwotę w odpowiedzi da się powiązać z obliczeniem. Kalkulator tylko
    liczy: to, czy kara się NALEŻY, zależy od umowy (warunki z kroku 1). Sprawdzenie polityki
    korzysta z twojego silnika reguł z Miniprojektu 3, tylko do odczytu. Wyszukiwanie zwraca
    surowe fragmenty z ich identyfikatorami: odpowiedź generuje agent, bez dodatkowego
    wywołania LLM-a wewnątrz narzędzia wyszukiwania.

WYNIK
        calculate_otif_penalty(otif_pct=94.6, target_pct=97, rate_per_full_point_pct=2,
                               cap_pct=10, invoice_grosze=18240000)
        -> PenaltyCalculation(status='ok', otif_pct=94.6, target_pct=97.0, rate_per_full_point_pct=2.0,
                              cap_pct=10.0, invoice_grosze=18240000, shortfall_points=2.4, full_points=2,
                              penalty_pct_uncapped=4.0, penalty_pct=4.0, penalty_grosze=729600, currency='PLN')

        check_discount_policy(config, discount_pct=22, margin_after_pct=7, strategic_account=True)
        -> PolicyCheck(status='ok', approvers=['Dyrektor handlowy', 'CFO'], reasons=[...],
                       version='course-v1', margin_checked=True, partial=False)

        search_documents(store, "Jaką karę płaci Mleczna Dolina za lipiec i dlaczego?", k=3)
        -> SearchResult(status='ok', query='Jaką karę płaci Mleczna Dolina za lipiec i dlaczego?',
                        passages=[Passage(doc_id='CON-101', chunk_id='CON-101#ctx003', text='...'), ...])

WYMAGANIA (sprawdzają je testy)
    calculate_otif_penalty(otif_pct, target_pct, rate_per_full_point_pct, cap_pct, invoice_grosze):
    - dokładna arytmetyka dziesiętna (Decimal(str(x)), bez działań arytmetycznych na typie float): 97 - 94,6 to
      2,4 punktu, a nie 2,4000000000000057;
    - shortfall_points = cel - OTIF, nigdy poniżej 0; full_points = jego część całkowita
      (brak 0,99 -> 0; dokładnie 1,0 -> 1);
    - penalty_pct_uncapped = full_points x stawka; penalty_pct = mniejsza z tej wartości i cap_pct;
    - penalty_grosze = invoice_grosze x penalty_pct / 100, zaokrąglone do pełnych groszy
      w górę od połowy (HALF UP), raz, na samym końcu (helpers.quantities.round_grosze):
      125 groszy x 2% = 2,5 -> 3 (round() w Pythonie dałoby 2: zaokrągla połówki do parzystej);
    - wynik powtarza dane wejściowe;
    - "invalid_request" (z message, bez kary), jeśli brakuje którejś wartości, nie jest liczbą
      (wartość logiczna True/False też nie jest liczbą, choć w Pythonie bool dziedziczy po int)
      albo nie jest skończona, OTIF lub cel wychodzi poza zakres 0–100, stawka jest ujemna, limit wychodzi
      poza 0–100 albo faktura nie jest całkowitą liczbą groszy >= 0.
      Komunikat nie może zależeć od tego, czy liczbę przekazano jako int, czy jako float (101
      i 101.0 dają ten sam komunikat): Miniprojekt 5 przesyła te wartości przez MCP, który
      może je przekonwertować.
    check_discount_policy(config, discount_pct, margin_after_pct=None, clearance=False,
                          strategic_account=False, competitor_offer=False,
                          contractual_volume_rebate=False):
    - wywołaj required_approvers z Miniprojektu 3 i przepisz approvers, reasons, version
      i margin_checked; partial ma wartość True, gdy marża była nieznana (minimalnej marży
      nie sprawdzono);
    - rabat wolumenowy z umowy z klientem to "out_of_scope": według POL-001 takie rabaty
      podlegają procesowi warunków kredytowych i handlowych, a nie tej polityce;
    - nieprawidłowe dane (required_approvers zgłasza ValueError) -> "invalid_request" z jego
      komunikatem;
    - nigdy niczego nie zatwierdza (mówi o tym pole note rekordu).
    search_documents(store, question, k):
    - wyszukiwanie z Miniprojektu 1 w store; każde trafienie jako Passage z doc_id, chunk_id
      i tekstem, od najlepszego; "no_results", jeśli nic nie znaleziono; "invalid_request"
      dla pustego pytania.

ZALECANE NARZĘDZIA
    decimal.Decimal; helpers.quantities.round_grosze; required_approvers z Miniprojektu 3;
    search z Miniprojektu 1. Przykłady: „Przybornik” w mini_project_4/README.md.

NA KONIEC SPRAWDŹ KOD POLECENIEM
    uv run pytest mini_project_4/tests/test_step2_compute_and_search.py -v
"""

import math
from decimal import Decimal

from helpers.company import Passage, PenaltyCalculation, PolicyCheck, SearchResult
from helpers.config import Config
from helpers.quantities import round_grosze
from helpers.workflow import DiscountRequest
from mini_project_1.src.step5_search import search
from mini_project_3.src.step1_required_approvers import required_approvers


def calculate_otif_penalty(otif_pct: float, target_pct: float, rate_per_full_point_pct: float,
                           cap_pct: float, invoice_grosze: int) -> PenaltyCalculation:
    # TODO: twój kod – zobacz CEL, WYNIK i WYMAGANIA na początku pliku
    raise NotImplementedError("TODO: calculate_otif_penalty")


def check_discount_policy(config: Config, discount_pct: float, margin_after_pct: float | None = None,
                          clearance: bool = False, strategic_account: bool = False,
                          competitor_offer: bool = False, contractual_volume_rebate: bool = False) -> PolicyCheck:
    # TODO: twój kod – zobacz CEL, WYNIK i WYMAGANIA na początku pliku
    raise NotImplementedError("TODO: check_discount_policy")


def search_documents(store, question: str, k: int) -> SearchResult:
    # TODO: twój kod – zobacz CEL, WYNIK i WYMAGANIA na początku pliku
    raise NotImplementedError("TODO: search_documents")
