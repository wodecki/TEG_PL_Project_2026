"""Liczby, jednostki i frazy w odpowiedziach i wynikach narzędzi. Gotowy plik: nie edytujesz go.

Program oceniający w Miniprojekcie 4 pyta: czy ta liczba z odpowiedzi ma pokrycie w wyniku
narzędzia? Zwykłe porównywanie napisów myli się tu na kilka sposobów. Ten moduł obsługuje je jawnie:
  - jednostki: wynik ma penalty_grosze = 729600, a odpowiedź mówi „7296,00 zł”. Pola
    z końcówką _grosze pokrywają obie formy (100 groszy = 1 PLN): „7296,00 PLN”
    i „729 600 groszy”, ale nigdy „729 600 PLN”;
  - rodzaje liczb: pola `_pct` to procenty, pola `_points` to punkty procentowe.
    „2%” i „2 punkty procentowe” to różne twierdzenia i mają pokrycie w różnych polach;
  - liczby, które nie są wielkościami: identyfikatory (SUP-114), daty (2026-07,
    20 sierpnia, 2026), okresy (Q2, H1) i numeracja list są pomijane;
  - formatowanie: najpierw usuwane są znaczniki formatowania Markdown (**pogrubienie**, _kursywa_, `kod`),
    więc „**729 600** groszy” zachowuje jednostkę; minus zostaje („-7296 zł” jest ujemne).

Polskie formy, które moduł czyta (obok angielskich):
  - przecinek dziesiętny: „2,5%”, „94,6 procent”, „7296,00 zł”;
  - grupowanie cyfr spacją, także twardą (U+00A0) i wąską (U+202F): „18 240 000”,
    „7 296,00 zł”;
  - jednostki: „%”, „procent…”, „proc.”; „punkt…”, „pkt”, „punkty procentowe”, „pkt proc.”,
    „pp” (z opcjonalnym „pełne”); „zł”, „złotych”, „PLN” (także przed liczbą: „PLN 12”);
    „groszy”, „grosze”, „gr”;
  - daty: „20 sierpnia” (miesiące w dopełniaczu) są pomijane jak „20 August”.

Reguła niejednoznaczności (`_ambiguous`): liczba z jednym przecinkiem, po którym stoją dokładnie
trzy cyfry, i co najwyżej trzema cyframi przed nim (np. „1,500”), może oznaczać liczbę dziesiętną w polskiej notacji
(1,5) albo liczbę z separatorem tysięcy w notacji angielskiej (1500). Moduł nie zgaduje i nigdy nie rozstrzyga jej na korzyść tego, co mówi
wynik narzędzia: taka liczba jest oznaczona `ambiguous=True`, a `same_quantity` uznaje, że
nie jest równa niczemu (nie pokrywa i nie jest pokryta). Program oceniający ją zgłasza.
Jednoznaczne są: „1500”, „1 500”, „1,5”, „7,296.00” (przecinek grupuje tysiące, gdy jest
też kropka), „1,500,000” (kilka przecinków grupujących).

Znane ograniczenia: liczby zapisane słowami („trzy”) nie są czytane, a liczba bez jednostki
zgadza się z każdą jednostką.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

_MONTHS = ("january|february|march|april|may|june|july|august|september|october|november|december"
           "|jan|feb|mar|apr|jun|jul|aug|sep|sept|oct|nov|dec"
           "|stycznia|lutego|marca|kwietnia|maja|czerwca|lipca|sierpnia|września|października|listopada|grudnia")
# fragmenty z cyframi, które nie są wielkościami
_SKIP = re.compile(
    r"\b[A-Z]{2,5}-\d+(?:#\w+)?\b"                           # identyfikatory: SUP-114, CON-101, POL-001#ctx002
    r"|\b\d{4}-\d{2}(?:-\d{2})?\b"                           # daty: 2026-07, 2026-08-20
    r"|\b\d{1,2}\.\d{1,2}\.\d{4}\b"                         # daty w polskim zapisie: 31.03.2027
    r"|\b[QH][1-4]\b"                                        # okresy: Q2, H1
    rf"|\b\d{{1,2}}(?:st|nd|rd|th)?\s+(?:{_MONTHS})\b"       # 20 August, 20 sierpnia
    rf"|\b(?:{_MONTHS})\s+\d{{1,2}}(?:st|nd|rd|th)?\b(?!\s*[%.,]?\d)"  # August 20
    r"|^[ \t]*(?:[-*][ \t]+)?\d{1,2}[.)][ \t]",              # numeracja listy na początku wiersza
    re.IGNORECASE | re.MULTILINE)
_NUMBER = re.compile(
    r"(?<![\w.,])(?P<num>\d{1,3}(?:[   ,]\d{3})+(?:\.\d+|,\d{1,2}(?!\d))?|\d+(?:[.,]\d+)?)(?![\w])")
_UNIT_AFTER = [
    ("pp", re.compile(r"\s*(?:full\s+)?(?:percentage\s+)?(?:points?\b|pp\b|p\.p\.)"
                      r"|\s*(?:pełn\w*\s+)?(?:punkt\w*|pkt\.?)(?:\s+proc(?:entow\w*|\.))?(?!\w)",
                      re.IGNORECASE)),
    ("%", re.compile(r"\s*(?:%|per ?cent\b|percent\b|procent\w*|proc\.)", re.IGNORECASE)),
    ("PLN", re.compile(r"\s*(?:PLN|zł(?!\w)|złot\w*|zl\b|zloty\b)", re.IGNORECASE)),
    ("grosze", re.compile(r"\s*(?:grosze|groszy|grosz|gr)\b", re.IGNORECASE)),
]
_UNIT_BEFORE = re.compile(r"(?:PLN|zł)\s*$", re.IGNORECASE)
_MARKDOWN = re.compile(r"[*_`]+")
_MINUS = "-\u2212"                                      # łącznik-minus i znak minus
_YEAR = re.compile(r"(?:19|20)\d{2}")


@dataclass(frozen=True)
class Quantity:
    value: Decimal
    unit: str | None          # "PLN", "grosze", "%" (procent), "pp" (punkty procentowe) albo None (sama liczba)
    text: str                 # tak, jak zapisano
    ambiguous: bool = False   # "1,500": po polsku 1,5, po angielsku 1500. Nigdy nie pokrywa i nie jest pokryta.


def _ambiguous(token: str) -> bool:
    """Jeden przecinek, po nim dokładnie trzy cyfry, nic więcej: „1,500” po polsku to 1,5,
    a po angielsku 1500. Tu tego nie rozstrzygamy, a już na pewno nie na korzyść źródła."""
    head, comma, tail = token.partition(",")
    return bool(comma) and "," not in tail and len(tail) == 3 and head.isdigit() and len(head) <= 3 \
        and tail.isdigit()


def _value(token: str) -> Decimal:
    token = token.replace(" ", "").replace(" ", "").replace(" ", "")
    if "," in token and "." in token:                       # 7,296.00: przecinek grupuje tysiące
        token = token.replace(",", "")
    elif "," in token:
        head, _, tail = token.rpartition(",")
        if len(tail) == 3:                                   # 7,296 / 1,500,000: grupowanie
            token = token.replace(",", "")
        else:                                                # 2,5 / 7296,00: przecinek dziesiętny
            token = head.replace(",", "") + "." + tail
    return Decimal(token)


def numbers_in(text: str) -> list[Quantity]:
    """Każda wielkość zapisana cyframi w `text`, z jednostką, jeśli stoi tuż obok.

        numbers_in("Lipiec: 94,6%, o 2 pełne punkty poniżej; kara 7296,00 zł (CON-101, 2026-07)")
        -> [Quantity(94.6, '%'), Quantity(2, 'pp'), Quantity(7296.00, 'PLN')]
    """
    if not text:
        return []
    text = _MARKDOWN.sub("", text)
    masked = _SKIP.sub(lambda m: " " * len(m.group()), text)
    found = []
    for match in _NUMBER.finditer(masked):
        token, rest = match.group("num"), masked[match.end():]
        before = masked[:match.start()]
        negative = before[-1:] != "" and before[-1] in _MINUS and (len(before) < 2 or before[-2] in " \t\n(:=")
        unit = next((name for name, pattern in _UNIT_AFTER if pattern.match(rest)), None)
        if unit is None and _UNIT_BEFORE.search(masked[:match.start()]):
            unit = "PLN"
        if unit is None and _YEAR.fullmatch(token):         # samo 2026 to rok, a nie wielkość
            continue
        value = _value(token)
        found.append(Quantity(-value if negative else value, unit, ("-" if negative else "") + token,
                              ambiguous=_ambiguous(token)))
    return found


def _field_unit(key: str) -> str | None:
    if key.endswith("_grosze"):
        return "PLN"
    if key.endswith("_pct"):
        return "%"
    if key.endswith("_points"):
        return "pp"
    return None


def source_values(result: object, key: str = "") -> list[Quantity]:
    """Każda wielkość, którą podaje wynik narzędzia: jego pola liczbowe z jednostką wynikającą
    z nazwy pola (pole _grosze podaje wartość i w groszach, i w PLN) oraz liczby zapisane w jego
    polach tekstowych (fragmentach dokumentów)."""
    if isinstance(result, dict):
        return [q for k, v in result.items() for q in source_values(v, k)]
    if isinstance(result, list):
        return [q for item in result for q in source_values(item, key)]
    if isinstance(result, bool) or result is None:
        return []
    if isinstance(result, (int, float)):
        unit = _field_unit(key)
        value = Decimal(str(result))
        if unit == "PLN":                                    # całkowite grosze: obie formy
            return [Quantity(value / 100, "PLN", str(result)), Quantity(value, "grosze", str(result))]
        return [Quantity(value, unit, str(result))]
    if isinstance(result, str):
        return numbers_in(result)
    return []


def same_quantity(claim: Quantity, source: Quantity) -> bool:
    """Równe co do grosza, a jednostki są zgodne. Liczba bez jednostki zgadza się z każdą jednostką.
    Liczba niejednoznaczna („1,500”) nie zgadza się z niczym: zgłaszamy ją, a nie zgadujemy."""
    if claim.ambiguous or source.ambiguous:
        return False
    if claim.value.quantize(Decimal("0.01")) != source.value.quantize(Decimal("0.01")):
        return False
    return claim.unit is None or source.unit is None or claim.unit == source.unit


def grosze_to_pln(grosze: int) -> Decimal:
    """729600 -> Decimal('7296.00')"""
    return (Decimal(grosze) / 100).quantize(Decimal("0.01"))


def round_grosze(amount: Decimal) -> int:
    """Zaokrągla kwotę w groszach do pełnych groszy, połówki w górę: 2.5 -> 3, 246.4 -> 246."""
    return int(Decimal(amount).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def mentions(text: str, phrase: str) -> bool:
    """True, jeśli `phrase` występuje w `text` jako cała fraza: bez względu na wielkość liter,
    dowolne białe znaki liczą się jak jedna spacja, Markdown w tekście jest pomijany, nigdy
    wewnątrz dłuższego słowa ani liczby („nota” nie występuje w „notatka”; „7296” nie występuje
    w „27 296” ani w „-7296”; „9%” nie występuje w „19,9%”; „500 000” nie występuje w „1 500 000”)."""
    def normalise(value: str) -> str:
        return re.sub(r"\s+", " ", value).casefold()

    phrase = normalise(_MARKDOWN.sub("", phrase))
    # liczba nigdy nie pasuje wewnątrz dłuższej ani po znaku minus („7296” nie występuje w „-7296”)
    before = r"(?<!\w)(?<!\d[.,])" + (r"(?<!\d )(?<![\s(:=][-\u2212])(?<!^[-\u2212])" if phrase[:1].isdigit() else "")
    after = r"(?!\w)(?![.,]\d)" + (r"(?! \d)" if phrase[-1:].isdigit() else "")
    return re.search(before + re.escape(phrase) + after, normalise(_MARKDOWN.sub("", text or ""))) is not None
