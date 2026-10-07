"""Wczytuje katalog korpusu. Gotowy plik: nie edytujesz go."""

from __future__ import annotations

import csv
from pathlib import Path


def load_catalog(catalog_path: Path) -> dict[str, dict]:
    """Katalog jako {nazwa pliku: wiersz}.

    Przykład: load_catalog(path)["POL-001_discount_approval_policy.md"]
              -> {"doc_id": "POL-001", "file": "POL-001_...md", "title": "Polityka akceptacji rabatów", ...}
    """
    catalog_path = Path(catalog_path)
    if not catalog_path.is_file():
        raise FileNotFoundError(f"Nie znaleziono katalogu korpusu: {catalog_path}")
    with catalog_path.open(encoding="utf-8", newline="") as fh:
        return {row["file"]: row for row in csv.DictReader(fh)}
