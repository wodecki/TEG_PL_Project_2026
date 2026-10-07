"""KROK 1: Polityka rabatowa jako kod

CEL
    Ustal, kto musi zatwierdzić rabat, dokładnie według kursowej interpretacji
    polityki rabatowej POL-001. Zwykłym kodem, bez LLM: model tylko odczyta
    wiadomość menedżera (krok 2), a reguły stosujesz tutaj, za każdym razem
    tak samo i z wypisanym uzasadnieniem.

WYNIK
    required_approvers(request, config) zwraca Decision (helpers/workflow.py):

        required_approvers(DiscountRequest(discount_pct=7, margin_after_pct=8), config)
        -> Decision(approvers=['Regionalny kierownik sprzedaży', 'CFO'],
                    reasons=['rabat 7% mieści się w przedziale do 12%; zatwierdza: Regionalny kierownik sprzedaży (tabela POL-001)',
                             'marża 8% jest niższa od minimalnej (9%); dochodzi: CFO (minimalna marża, POL-001)'],
                    margin_checked=True, version='course-v1')

    (brzmienie uzasadnień zależy od ciebie; testy sprawdzają osoby zatwierdzające)

WYMAGANIA (sprawdzają je testy) – kursowa interpretacja „course-v1”
    Wartości odczytaj z config.get("policy"): bands, exceptions, margin_floor,
    floor_role, version. Potem, w tej kolejności:
    1. Zwykły przedział: pierwszy przedział, którego up_to jest >= rabatu
       (5% -> przedział do 5%; 5,01% -> następny). Jego role to podstawowe
       osoby zatwierdzające.
    2. Wyjątki, które mają zastosowanie: flaga ma wartość True ORAZ rabat
       nie przekracza limitu wyjątku (cap).
    3. Wybierany jest najniższy uprawniony poziom. Porównaj podstawowy przedział z rolami
       każdego mającego zastosowanie wyjątku według poziomu uprawnień, czyli pozycji
       ich przedziału w config["bands"] (przedstawiciel handlowy najniżej, CEO + CFO
       najwyżej). Wyjątek może obniżyć poziom uprawnień, ale nigdy go nie podnosi:
       rabat 3% dla klienta strategicznego nadal zatwierdza przedstawiciel handlowy.
    4. Minimalna marża: jeśli margin_after_pct jest niższa niż margin_floor (równo
       9% wystarcza), a towar NIE jest objęty wyprzedażą końcówek, dodaj floor_role (CFO)
       na końcu listy, o ile jeszcze go na niej nie ma. Wyprzedaż końcówek jest
       zwolniona z minimalnej marży także powyżej swojego limitu rabatu.
    5. margin_checked ma wartość False, gdy margin_after_pct to None (nie dało się
       sprawdzić minimalnej marży); wtedy reguła minimalnej marży nie dodaje osoby zatwierdzającej.
    6. Każda reguła, która wpłynęła na wynik, dodaje jedną pozycję do reasons
       (marża poniżej minimalnej jest zawsze wyjaśniona, nawet gdy floor_role
       i tak jest już na liście); version to config["version"].
    Nieprawidłowe dane: ValueError z nazwą pola. Dotyczy to rabatu, którego brak,
    który nie jest skończoną liczbą albo wychodzi poza zakres 0–100, oraz marży
    spoza zakresu -100–100 lub nieskończonej.

ZALECANE NARZĘDZIA
    Zwykły Python; math.isfinite. Przykłady: „Przybornik” w mini_project_3/README.md.

NA KONIEC SPRAWDŹ KOD POLECENIEM
    uv run pytest mini_project_3/tests/test_step1_required_approvers.py -v
"""

import math

from helpers.config import Config
from helpers.text_pl import number          # gotowa funkcja: 5.01 -> "5,01" (tylko w tekście dla ludzi)
from helpers.workflow import Decision, DiscountRequest

EXCEPTION_NAMES = {"clearance": "wyprzedaż końcówek", "strategic_account": "klient strategiczny",
                   "competitor_offer": "oferta konkurencji"}


def required_approvers(request: DiscountRequest, config: Config) -> Decision:
    # TODO: twój kod – zobacz CEL, WYNIK i WYMAGANIA na początku pliku
    raise NotImplementedError("TODO: required_approvers")
