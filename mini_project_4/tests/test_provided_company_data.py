"""Gotowe testy: twoje narzędzia na PRAWDZIWYCH danych firmy dają wartości wzorcowe policzone ręcznie,
a uszkodzone pliki danych kończą się wyraźnym błędem.

Wzorzec w data/eval/mini_project_4_questions.yaml policzono ręcznie; nic tutaj nie liczy go
testowanym kodem.
"""

import shutil

import pytest

from helpers.company import CompanyDataError, load_company_data
from helpers.config import Config
from mini_project_4.src.step1_read_company_data import get_contract_terms, get_invoice_value, get_supplier_otif
from mini_project_4.src.step2_compute_and_search import calculate_otif_penalty

HAND_WORKED = {"2026-07": 729600, "2026-06": 362400, "2026-05": 0}   # grosze: 7296,00 / 3624,00 / 0 PLN


def test_every_gold_calculation_matches_the_data_and_the_hand_worked_penalty(company_data, gold):
    for question in gold.values():
        for g in question.calculations:
            otif = get_supplier_otif(company_data, g.supplier_id, g.month, g.month)
            terms = get_contract_terms(company_data, g.supplier_id)
            invoice = get_invoice_value(company_data, g.supplier_id, g.month)
            assert otif.observations[0].otif_pct == g.otif_pct, f"{question.id}: OTIF"
            assert (terms.otif_target_pct, terms.rate_per_full_point_pct, terms.cap_pct) == \
                (g.target_pct, g.rate_per_full_point_pct, g.cap_pct), f"{question.id}: terms"
            assert invoice.invoiced_grosze == g.invoice_grosze, f"{question.id}: invoice"
            result = calculate_otif_penalty(g.otif_pct, g.target_pct, g.rate_per_full_point_pct, g.cap_pct, g.invoice_grosze)
            assert result.penalty_grosze == HAND_WORKED[g.month], f"{question.id}: penalty"


def test_the_termination_months(company_data):
    result = get_supplier_otif(company_data, "Mleczna Dolina", "2026-07", "2026-10")
    assert [(o.month, o.otif_pct) for o in result.observations] == [("2026-07", 94.6), ("2026-08", 93.8), ("2026-09", 93.5)]
    assert result.missing_months == ["2026-10"]


def test_aqua_missed_its_target_without_a_penalty_clause(company_data):
    terms = get_contract_terms(company_data, "Aqua Kryształ")
    assert (terms.source_doc_id, terms.otif_target_pct, terms.penalty_clause) == ("CON-102", 96, False)
    assert get_supplier_otif(company_data, "SUP-207", "2026-07", "2026-07").observations[0].otif_pct == 95.1


def test_transbalt_never_feeds_an_otif_calculation(company_data):
    terms = get_contract_terms(company_data, "TransBałt")
    assert terms.status == "not_applicable" and terms.source_doc_id == "CON-103"
    assert terms.otif_target_pct is None


def test_october_has_no_data_yet(company_data):
    assert get_supplier_otif(company_data, "SUP-114", "2026-10", "2026-10").status == "no_data"


@pytest.fixture
def broken(config, tmp_path):
    """Kopia data/company/, w której można podmienić jeden wiersz jednego pliku."""
    folder = tmp_path / "company"
    shutil.copytree(config.path("paths.company_data_dir"), folder)
    raw = {**config.raw, "paths": {**config.raw["paths"], "company_data_dir": str(folder)}}

    def make(file: str, old: str, new: str) -> Config:
        path = folder / file
        text = path.read_text(encoding="utf-8")
        assert old in text
        path.write_text(text.replace(old, new, 1), encoding="utf-8")
        return Config(root=config.root, raw=raw)
    return make


@pytest.mark.parametrize("file, old, new, says", [
    ("supplier_otif.csv", "SUP-114,2026-08,93.8", "SUP-114,2026-07,93.8", "zduplikowany"),
    ("supplier_otif.csv", "2026-08,93.8", "2026-8,93.8", "YYYY-MM"),
    ("supplier_otif.csv", "93.8", "938", "od 0 do 100"),
    ("supplier_otif.csv", "93.8", "n/a", "nie jest liczbą"),
    ("supplier_otif.csv", "SUP-207,2026-05", "SUP-999,2026-05", "nieznany dostawca"),
    ("supplier_invoices.csv", "18240000", "182400.00", "całkowitą liczbą groszy"),
    ("supplier_invoices.csv", "18240000,PLN", "18240000,EUR", "PLN"),
])
def test_a_broken_file_is_an_error_not_no_data(broken, file, old, new, says):
    with pytest.raises(CompanyDataError, match=says):
        load_company_data(broken(file, old, new))
