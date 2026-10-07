# data/company/: dane firmy Kovalo (fikcyjny stan na konkretny dzień, tylko do odczytu)

Stan na dzień: **2026-10-01**. Narzędzia Miniprojektu 4 odczytują dane z tych plików. Dane nie są aktualizowane na bieżąco.

| Plik | Co zawiera | Skąd pochodzą wartości |
|---|---|---|
| `suppliers.csv` | identyfikator dostawcy, nazwa, dokument umowy | umowy CON-101, CON-102 |
| `supplier_otif.csv` | miesięczny OTIF każdego dostawcy, w procentach | kolumna `source`: wiersze `MTG-403` powtarzają tabelę ze spotkania (Mleczna Dolina, maj–lipiec); wiersze `scenario` to nowe dane do ćwiczenia |
| `supplier_invoices.csv` | miesięczna wartość faktur każdego dostawcy, w **całkowitych groszach** (100 groszy = 1 PLN) | `scenario`: nowe dane do ćwiczenia |
| `contract_terms.yaml` | miesięczne warunki OTIF z umowy każdego dostawcy | wybrane i uporządkowane zapisy CON-101 i CON-102, sprawdzone z ich tekstem; CON-103 (TransBałt) figuruje jako umowa **bez** OTIF |

Za październik 2026 r. nie ma jeszcze danych: narzędzie zwraca dla tego miesiąca zwykły wynik „brak danych”, a nie błąd.
