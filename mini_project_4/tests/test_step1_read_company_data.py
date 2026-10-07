"""Testy kroku 1: narzędzia danych mówią, o co pytano, co znaleziono i czego brakuje."""

import pytest

from mini_project_4.src.step1_read_company_data import get_contract_terms, get_invoice_value, get_supplier_otif


def months(result):
    return [(o.month, o.otif_pct) for o in result.observations]


def test_a_full_period_is_sorted_and_complete(small_data):
    result = get_supplier_otif(small_data, "SUP-114", "2026-08", "2026-09")
    assert result.status == "ok"
    assert (result.supplier_id, result.supplier) == ("SUP-114", "Mleczna Dolina")
    assert months(result) == [("2026-08", 94.0), ("2026-09", 93.5)], "observations muszą być posortowane według miesiąca, z niezmienionymi wartościami"
    assert result.missing_months == [] and result.complete is True
    assert result.requested == {"from": "2026-08", "to": "2026-09"}


def test_a_missing_end_month_is_reported_not_dropped(small_data):
    result = get_supplier_otif(small_data, "Mleczna Dolina", "2026-08", "2026-10")
    assert result.status == "ok", "niepełny okres to nadal 'ok'..."
    assert months(result) == [("2026-08", 94.0), ("2026-09", 93.5)]
    assert result.missing_months == ["2026-10"], "...ale wynik musi podać, których miesięcy brakuje"
    assert result.complete is False


def test_a_missing_middle_month_is_reported(small_data):
    # maj, czerwiec, sierpień i wrzesień mają dane, lipiec nie: obserwacje nie są kolejnymi miesiącami
    result = get_supplier_otif(small_data, "SUP-114", "2026-05", "2026-09")
    assert [m for m, _ in months(result)] == ["2026-05", "2026-06", "2026-08", "2026-09"]
    assert result.missing_months == ["2026-07"] and result.complete is False


def test_a_period_across_the_new_year(small_data):
    result = get_supplier_otif(small_data, "SUP-114", "2026-11", "2027-01")
    assert result.status == "no_data"
    assert result.missing_months == ["2026-11", "2026-12", "2027-01"]
    assert result.supplier_id == "SUP-114", "brak danych nadal dotyczy znanego dostawcy"


@pytest.mark.parametrize("supplier", ["sup-114", "Mleczna Dolina", "MLECZNA DOLINA", "Mleczna"])
def test_suppliers_are_resolved_by_id_or_name(small_data, supplier):
    assert get_supplier_otif(small_data, supplier, "2026-06", "2026-06").supplier_id == "SUP-114"


def test_polish_letters_are_optional(small_data):
    assert get_supplier_otif(small_data, "Aqua Krysztal", "2026-07", "2026-07").supplier_id == "SUP-207"


def test_an_unknown_supplier(small_data):
    result = get_supplier_otif(small_data, "Nordic Fish", "2026-07", "2026-07")
    assert result.status == "unknown_supplier" and result.observations == []
    assert result.message, "podaj, którego dostawcy nie znaleziono"


@pytest.mark.parametrize("from_month, to_month", [("2026-7", "2026-07"), ("July", "2026-07"), ("2026-13", "2026-13"),
                                                  ("2026-09", "2026-07"), ("2026-07-01", "2026-07")])
def test_invalid_periods(small_data, from_month, to_month):
    result = get_supplier_otif(small_data, "SUP-114", from_month, to_month)
    assert result.status == "invalid_request", f"{from_month}..{to_month} to nieprawidłowy okres"
    assert result.requested == {"from": from_month, "to": to_month}
    assert result.observations == []


def test_invoice_in_grosze(small_data):
    result = get_invoice_value(small_data, "Mleczna Dolina", "2026-06")
    assert (result.status, result.supplier_id, result.month) == ("ok", "SUP-114", "2026-06")
    assert result.invoiced_grosze == 18120000 and isinstance(result.invoiced_grosze, int)
    assert result.currency == "PLN"


def test_an_absent_invoice_is_no_data(small_data):
    result = get_invoice_value(small_data, "SUP-114", "2026-07")
    assert result.status == "no_data" and result.invoiced_grosze is None
    assert result.supplier_id == "SUP-114"


def test_invoice_outcomes(small_data):
    assert get_invoice_value(small_data, "Nordic Fish", "2026-06").status == "unknown_supplier"
    assert get_invoice_value(small_data, "SUP-114", "June 2026").status == "invalid_request"


def test_terms_with_a_penalty_clause(small_data):
    result = get_contract_terms(small_data, "Mleczna Dolina")
    assert result.status == "ok"
    assert (result.supplier_id, result.source_doc_id, result.terms_version) == ("SUP-114", "CON-101", "terms-test")
    assert (result.otif_target_pct, result.penalty_clause, result.rate_per_full_point_pct, result.cap_pct) == (97, True, 2, 10)


def test_no_clause_is_not_a_zero_rate(small_data):
    result = get_contract_terms(small_data, "SUP-207")
    assert result.status == "ok" and result.otif_target_pct == 96
    assert result.penalty_clause is False, "umowa z Aqua Kryształ NIE ma klauzuli kary umownej"
    assert result.rate_per_full_point_pct is None and result.cap_pct is None, "brak klauzuli musi zostać None, nigdy 0"


def test_transbalt_has_no_otif_terms(small_data):
    result = get_contract_terms(small_data, "TransBałt")
    assert result.status == "not_applicable", "98% w CON-103 dotyczy palet dostarczonych na czas, a nie miesięcznego OTIF"
    assert result.source_doc_id == "CON-103"
    assert result.otif_target_pct is None and result.rate_per_full_point_pct is None
    assert result.message


def test_a_known_supplier_without_terms(small_data):
    result = get_contract_terms(small_data, "Test Foods")
    assert result.status == "not_applicable" and result.supplier_id == "SUP-300"


def test_an_unknown_party(small_data):
    assert get_contract_terms(small_data, "Nordic Fish").status == "unknown_supplier"
