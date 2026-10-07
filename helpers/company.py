"""Dane firmy Kovalo i rekordy wyników narzędzi z Miniprojektu 4. Gotowy plik: nie edytujesz go.

Każde narzędzie zwraca jeden z poniższych rekordów jako JSON. Dla wszystkich obowiązują trzy zasady:
  - `status` mówi, co się stało. "ok" to wynik; "no_data", "unknown_supplier",
    "not_applicable", "out_of_scope" i "invalid_request" to ZWYKŁE odpowiedzi, na które agent
    może zareagować. Uszkodzony plik danych nigdy nie jest jedną z nich: wtedy load_company_data
    zgłasza wyjątek.
  - Jednostki są w nazwach pól: `_pct` to procenty, `_points` punkty procentowe, `_grosze`
    całkowita liczba groszy (100 groszy = 1 PLN). Kwoty nigdy nie są typu float.
  - Identyfikatory są kanoniczne (SUP-114, CON-101); miesiące mają format YYYY-MM.
"""

from __future__ import annotations

import csv
import math
import re
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field

from helpers.config import Config, ConfigError


class CompanyDataError(ConfigError):
    """Brakuje pliku danych firmy albo jest uszkodzony. Nigdy nie jest zgłaszany jako „brak danych”."""


# --- rekordy zwracane przez narzędzia -------------------------------------------------------

class OtifObservation(BaseModel):
    month: str                                   # YYYY-MM
    otif_pct: float


class OtifResult(BaseModel):
    """get_supplier_otif: miesięczny OTIF dostawcy w danym okresie."""

    status: Literal["ok", "no_data", "unknown_supplier", "invalid_request"]
    supplier_id: str | None = None               # kanoniczny identyfikator, gdy dostawca jest znany
    supplier: str | None = None                  # jego nazwa
    requested: dict[str, str]                    # {"from": "2026-07", "to": "2026-10"}, tak jak w zapytaniu
    observations: list[OtifObservation] = Field(default_factory=list)   # posortowane według miesiąca
    missing_months: list[str] = Field(default_factory=list)            # miesiące z zapytania, dla których nie ma danych
    complete: bool = False                       # True tylko wtedy, gdy każdy miesiąc z zapytania ma dane
    message: str | None = None                   # dlaczego – przy wszystkim poza kompletnym "ok"


class InvoiceResult(BaseModel):
    """get_invoice_value: ile dostawca zafakturował Kovalo w jednym miesiącu."""

    status: Literal["ok", "no_data", "unknown_supplier", "invalid_request"]
    supplier_id: str | None = None
    supplier: str | None = None
    month: str
    invoiced_grosze: int | None = None
    currency: str = "PLN"
    message: str | None = None


class ContractTermsResult(BaseModel):
    """get_contract_terms: warunki umowy z dostawcą dotyczące miesięcznego OTIF."""

    status: Literal["ok", "unknown_supplier", "not_applicable"]
    supplier_id: str | None = None
    supplier: str | None = None
    source_doc_id: str | None = None             # dokument umowy, z którego pochodzą warunki
    otif_target_pct: float | None = None
    penalty_clause: bool | None = None           # False = umowa NIE MA klauzuli o karze umownej
    rate_per_full_point_pct: float | None = None  # None, gdy nie ma klauzuli (nigdy 0)
    cap_pct: float | None = None
    settlement: str | None = None
    terms_version: str | None = None
    message: str | None = None


class PenaltyCalculation(BaseModel):
    """calculate_otif_penalty: arytmetyka na podanych danych wejściowych, z każdą wartością pośrednią."""

    status: Literal["ok", "invalid_request"]
    otif_pct: float | None = None                # dane wejściowe, powtórzone
    target_pct: float | None = None
    rate_per_full_point_pct: float | None = None
    cap_pct: float | None = None
    invoice_grosze: int | None = None
    shortfall_points: float | None = None        # cel - OTIF, nigdy poniżej 0
    full_points: int | None = None               # pełne punkty niedoboru
    penalty_pct_uncapped: float | None = None
    penalty_pct: float | None = None             # po zastosowaniu limitu
    penalty_grosze: int | None = None
    currency: str = "PLN"
    note: str = "arytmetyka na podanych danych wejściowych; nie przesądza, czy kara się należy"
    message: str | None = None


class PolicyCheck(BaseModel):
    """check_discount_policy: kto musi zatwierdzić rabat (tylko informacja)."""

    status: Literal["ok", "out_of_scope", "invalid_request"]
    approvers: list[str] = Field(default_factory=list)
    reasons: list[str] = Field(default_factory=list)
    version: str | None = None                   # interpretacja polityki, np. course-v1
    margin_checked: bool = False
    partial: bool = False                        # True, gdy marża była nieznana: minimalnej marży nie sprawdzono
    note: str = "tylko informacja: to sprawdzenie niczego nie zatwierdza; wnioski o akceptację przechodzą przez workflow akceptacji (Miniprojekt 3)"
    message: str | None = None


class Passage(BaseModel):
    doc_id: str
    chunk_id: str
    text: str


class SearchResult(BaseModel):
    """search_documents: surowe fragmenty dokumentów Kovalo."""

    status: Literal["ok", "no_results", "invalid_request"]
    query: str
    passages: list[Passage] = Field(default_factory=list)
    message: str | None = None


# --- dane ---------------------------------------------------------------------------

MONTH = re.compile(r"\d{4}-(0[1-9]|1[0-2])")


def is_month(text: object) -> bool:
    """True dla napisu w formacie YYYY-MM, np. "2026-07"."""
    return isinstance(text, str) and MONTH.fullmatch(text) is not None


def month_range(from_month: str, to_month: str) -> list[str]:
    """Każdy miesiąc od from_month do to_month włącznie: ("2026-11", "2027-01") ->
    ["2026-11", "2026-12", "2027-01"]. Oba w formacie YYYY-MM; pusta lista, gdy from_month > to_month."""
    if not (is_month(from_month) and is_month(to_month)):
        raise ValueError(f"miesiące muszą mieć format YYYY-MM, otrzymano {from_month!r} i {to_month!r}")
    year, month = int(from_month[:4]), int(from_month[5:])
    months = []
    while f"{year:04d}-{month:02d}" <= to_month:
        months.append(f"{year:04d}-{month:02d}")
        year, month = (year + 1, 1) if month == 12 else (year, month + 1)
    return months


def _plain(text: str) -> str:
    """Małe litery, bez polskich znaków (ł -> l), pojedyncze spacje: do dopasowywania nazw dostawców."""
    text = unicodedata.normalize("NFKD", text.replace("ł", "l").replace("Ł", "L"))
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return re.sub(r"\s+", " ", text).strip().casefold()


@dataclass
class CompanyData:
    """Wczytane i sprawdzone dane firmy. Testy budują małe zestawy bezpośrednio."""

    suppliers: dict[str, str]                                    # supplier_id -> nazwa
    otif: dict[tuple[str, str], float]                           # (supplier_id, month) -> OTIF %
    invoices: dict[tuple[str, str], int]                         # (supplier_id, month) -> grosze
    terms: dict[str, dict] = field(default_factory=dict)         # supplier_id -> warunki OTIF (contract_terms.yaml)
    terms_version: str = ""
    not_otif: list[dict] = field(default_factory=list)           # umowy, w których poziom usług nie jest mierzony OTIF

    def resolve_supplier(self, text: str) -> str | None:
        """Kanoniczny identyfikator dostawcy na podstawie identyfikatora lub nazwy, bez względu na
        wielkość liter, z polskimi znakami lub bez ("sup-114", "Aqua Krysztal", "Mleczna Dolina");
        None, gdy dostawca jest nieznany albo niejednoznaczny."""
        query = _plain(str(text))
        if not query:
            return None
        for supplier_id, name in self.suppliers.items():
            if query in (_plain(supplier_id), _plain(name)):
                return supplier_id
        hits = [sid for sid, name in self.suppliers.items() if _plain(name) in query or query in _plain(name)]
        return hits[0] if len(hits) == 1 and len(query) >= 4 else None

    def not_otif_contract(self, text: str) -> dict | None:
        """Wpis not_otif dla strony umowy, np. "TransBałt", jeśli `text` ją wymienia."""
        query = _plain(str(text))
        return next((entry for entry in self.not_otif if query and (_plain(entry["name"]) in query or query in _plain(entry["name"]))), None)


def _rows(path: Path, columns: list[str]) -> list[dict]:
    if not path.is_file():
        raise CompanyDataError(f"Nie znaleziono pliku danych firmy: {path}")
    with path.open(encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        if reader.fieldnames != columns:
            raise CompanyDataError(f"{path.name}: oczekiwano kolumn {columns}, znaleziono {reader.fieldnames}")
        return list(reader)


def load_company_data(config: Config) -> CompanyData:
    """Wczytuje data/company/ (paths.company_data_dir) i sprawdza dane. Przy każdym błędzie
    zgłasza CompanyDataError z nazwą pliku i wiersza: zły miesiąc, wartość, która nie jest
    skończonym procentem, kwota, która nie jest całkowitą liczbą groszy, powtórzona para
    dostawca-miesiąc, nieznany dostawca."""
    folder = config.path("paths.company_data_dir")
    suppliers = {row["supplier_id"]: row["name"] for row in _rows(folder / "suppliers.csv", ["supplier_id", "name", "contract_doc_id"])}

    def key(row: dict, where: str) -> tuple[str, str]:
        if row["supplier_id"] not in suppliers:
            raise CompanyDataError(f"{where}: nieznany dostawca {row['supplier_id']!r}")
        if not is_month(row["month"]):
            raise CompanyDataError(f"{where}: miesiąc musi mieć format YYYY-MM, otrzymano {row['month']!r}")
        return row["supplier_id"], row["month"]

    otif: dict[tuple[str, str], float] = {}
    for n, row in enumerate(_rows(folder / "supplier_otif.csv", ["supplier_id", "month", "otif_pct", "source"]), start=2):
        where = f"supplier_otif.csv, wiersz {n}"
        k = key(row, where)
        try:
            value = float(row["otif_pct"])
        except ValueError:
            raise CompanyDataError(f"{where}: otif_pct nie jest liczbą: {row['otif_pct']!r}") from None
        if not math.isfinite(value) or not 0 <= value <= 100:
            raise CompanyDataError(f"{where}: otif_pct musi mieścić się w zakresie od 0 do 100, otrzymano {value}")
        if k in otif:
            raise CompanyDataError(f"{where}: zduplikowany wiersz dla {k[0]} {k[1]}")
        otif[k] = value

    invoices: dict[tuple[str, str], int] = {}
    for n, row in enumerate(_rows(folder / "supplier_invoices.csv", ["supplier_id", "month", "invoiced_grosze", "currency", "source"]), start=2):
        where = f"supplier_invoices.csv, wiersz {n}"
        k = key(row, where)
        if not row["invoiced_grosze"].isdigit():
            raise CompanyDataError(f"{where}: invoiced_grosze musi być całkowitą liczbą groszy, otrzymano {row['invoiced_grosze']!r}")
        if row["currency"] != "PLN":
            raise CompanyDataError(f"{where}: waluta musi być PLN, otrzymano {row['currency']!r}")
        if k in invoices:
            raise CompanyDataError(f"{where}: zduplikowany wiersz dla {k[0]} {k[1]}")
        invoices[k] = int(row["invoiced_grosze"])

    terms_path = folder / "contract_terms.yaml"
    if not terms_path.is_file():
        raise CompanyDataError(f"Nie znaleziono pliku danych firmy: {terms_path}")
    terms = yaml.safe_load(terms_path.read_text(encoding="utf-8"))
    unknown = set(terms["otif_terms"]) - set(suppliers)
    if unknown:
        raise CompanyDataError(f"contract_terms.yaml: nieznani dostawcy {sorted(unknown)}")
    return CompanyData(suppliers=suppliers, otif=otif, invoices=invoices, terms=terms["otif_terms"],
                       terms_version=terms["version"], not_otif=terms.get("not_otif", []))
