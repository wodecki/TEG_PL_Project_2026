"""KROK 1: Narzędzia jawnie opisujące dostępne i brakujące dane

CEL
    Trzy funkcje, które czytają dla agenta dane firmy Kovalo: miesięczny OTIF dostawcy,
    wartość jego faktury za miesiąc i warunki OTIF z jego umowy. Rzetelność odpowiedzi agenta
    zależy od wyników narzędzi. Zwrócenie danych za trzy miesiące zamiast czterech
    bez wskazania braku lub oznaczenie uszkodzonego pliku jako „brak danych” może
    prowadzić do błędnych wniosków. Dlatego każdy wynik jawnie określa zakres
    zapytania, znalezione dane i brakujące informacje.

WYNIK
    Rekordy z helpers/company.py (data to CompanyData, już wczytane i sprawdzone):

        get_supplier_otif(data, "Mleczna Dolina", "2026-08", "2026-10")
        -> OtifResult(status='ok', supplier_id='SUP-114', supplier='Mleczna Dolina',
                      requested={'from': '2026-08', 'to': '2026-10'},
                      observations=[OtifObservation(month='2026-08', otif_pct=93.8),
                                    OtifObservation(month='2026-09', otif_pct=93.5)],
                      missing_months=['2026-10'], complete=False,
                      message='brak danych za 2026-10')

        get_invoice_value(data, "SUP-114", "2026-07")
        -> InvoiceResult(status='ok', supplier_id='SUP-114', supplier='Mleczna Dolina',
                         month='2026-07', invoiced_grosze=18240000, currency='PLN')

        get_contract_terms(data, "TransBałt")
        -> ContractTermsResult(status='not_applicable', source_doc_id='CON-103',
                               message='poziom terminowych dostaw palet (98% palet w uzgodnionym
                                        oknie czasowym), bez części dotyczącej kompletności, ...')

    (brzmienie `message` zależy od ciebie; testy sprawdzają pola)

WYMAGANIA (sprawdzają je testy)
    Dostawca może być podany identyfikatorem albo nazwą w dowolnej formie: użyj
    data.resolve_supplier(text), które zwraca kanoniczny identyfikator (SUP-114) albo None.
    Gdy dostawca jest znany, każdy wynik zawiera supplier_id i supplier (nazwę
    z data.suppliers).
    get_supplier_otif(data, supplier, from_month, to_month):
    - "invalid_request", jeśli któryś miesiąc nie ma formatu YYYY-MM albo from_month > to_month
      (helpers: is_month, month_range); "requested" zawsze powtarza oba miesiące tak, jak je
      podano;
    - "unknown_supplier", jeśli nie da się ustalić dostawcy;
    - w pozostałych przypadkach każdy miesiąc okresu, łącznie z oboma końcami, jest albo
      obserwacją (posortowaną według miesiąca, niezależnie od kolejności w danych), albo
      trafia do missing_months; complete ma wartość True tylko wtedy, gdy niczego nie brakuje;
      status "ok", jeśli choć jeden miesiąc ma dane, "no_data", jeśli żaden. Niepełny okres
      to "ok" RAZEM z listą brakujących miesięcy.
    get_invoice_value(data, supplier, month): te same reguły "invalid_request" (miesiąc)
      i "unknown_supplier"; "no_data", gdy za ten miesiąc nie ma faktury; kwota jako liczba
      całkowita invoiced_grosze, currency "PLN".
    get_contract_terms(data, supplier):
    - znany dostawca z warunkami w data.terms: "ok" z każdym polem jego warunków
      (source_doc_id, otif_target_pct, penalty_clause, rate_per_full_point_pct, cap_pct,
      settlement) i terms_version = data.terms_version. Brak klauzuli to penalty_clause
      False oraz rate i cap równe None: nigdy nie zamieniaj „braku klauzuli” na 0;
    - znany dostawca bez warunków w data.terms: "not_applicable" z supplier_id i message
      mówiącym, że w danych nie ma jego warunków OTIF (source_doc_id zostaje None);
    - strona umowy wymieniona w data.not_otif (data.not_otif_contract(text)): "not_applicable"
      z source_doc_id i reason tego wpisu (reason jako message). Poziom usług z takiej umowy
      to nie miesięczny OTIF, więc nie może posłużyć do obliczenia kary umownej;
    - w pozostałych przypadkach "unknown_supplier".
    Przy tych zwykłych wynikach nigdy nie zgłaszaj wyjątku.

ZALECANE NARZĘDZIA
    Rekordy i funkcje pomocnicze z helpers/company.py: CompanyData.resolve_supplier,
    CompanyData.not_otif_contract, is_month, month_range. Przykłady: „Przybornik”
    w mini_project_4/README.md.

NA KONIEC SPRAWDŹ KOD POLECENIEM
    uv run pytest mini_project_4/tests/test_step1_read_company_data.py -v
"""

from helpers.company import (CompanyData, ContractTermsResult, InvoiceResult, OtifObservation, OtifResult,
                             is_month, month_range)


def get_supplier_otif(data: CompanyData, supplier: str, from_month: str, to_month: str) -> OtifResult:
    # TODO: twój kod – zobacz CEL, WYNIK i WYMAGANIA na początku pliku
    raise NotImplementedError("TODO: get_supplier_otif")


def get_invoice_value(data: CompanyData, supplier: str, month: str) -> InvoiceResult:
    # TODO: twój kod – zobacz CEL, WYNIK i WYMAGANIA na początku pliku
    raise NotImplementedError("TODO: get_invoice_value")


def get_contract_terms(data: CompanyData, supplier: str) -> ContractTermsResult:
    # TODO: twój kod – zobacz CEL, WYNIK i WYMAGANIA na początku pliku
    raise NotImplementedError("TODO: get_contract_terms")
