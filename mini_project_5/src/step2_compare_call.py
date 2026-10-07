"""KROK 2: Zgodność wyników: czy ścieżka przez MCP zwraca dokładnie to samo co wywołanie bezpośrednie?

CEL
    To samo wywołanie, wykonane bezpośrednio (funkcja z Miniprojektu 4) i przez serwer MCP, musi
    dać ten sam rekord: te same pola, te same wartości, te same typy JSON. Jeśli tak nie jest,
    nakładka albo transport coś zmieniły. Trzeba wtedy wiedzieć, CO się zmieniło, i to na tyle
    dokładnie, żeby dało się to naprawić. Zgodność sprawdza połączenie (nakładkę i transport), nie
    odpowiedź biznesową: dwie ścieżki, które korzystają z tej samej błędnej funkcji, zgadzają się
    idealnie. Dlatego odpowiedzi nadal ocenia wzorzec z Miniprojektów 3 i 4.

WYNIK
    compare_call(direct, mcp) porównuje dwa rekordy JSON i wymienia każdą różnicę:

        compare_call({"invoiced_grosze": 18240000, "currency": "PLN"},
                     {"invoiced_grosze": 182400.0, "currency": "PLN", "note": "x"})
        -> {"same": False,
            "differences": [{"path": "invoiced_grosze", "kind": "unit", "direct": 18240000, "mcp": 182400.0},
                            {"path": "note", "kind": "extra", "direct": None, "mcp": "x"}]}

WYMAGANIA (sprawdzają je testy)
    Porównuj odpowiadające sobie elementy obu rekordów (słowniki po kluczach, listy po pozycjach; ścieżki w rodzaju
    "observations[1].otif_pct"). Każda różnica to jeden słownik z polami path, kind, direct i mcp
    (None tam, gdzie po danej stronie nic nie ma). Rodzaje (kind), w tej kolejności pierwszeństwa:
    - "missing": jest w direct, brak w mcp (dotyczy też elementu listy); "extra": odwrotnie;
    - "unit": pole, którego nazwa kończy się na "_grosze", gdy wartość mcp nie jest int albo
      mcp x 100 == direct (nakładka zamieniła grosze na złotówki). Wartość true/false w formacie JSON nie jest
      tu int, choć w Pythonie bool jest podklasą int (isinstance(True, int) daje True).
      "unit" ma pierwszeństwo przed "type": invoiced_grosze 18240000 wobec 18240000.0 to "unit",
      bo pole groszowe przyszło jako float;
    - "type": wartości różnią się tylko typem JSON: 97 vs 97.0, "5" vs 5, true vs 1, null vs "None".
      Ściśle: reprezentacja jest częścią kontraktu, więc to są różnice, nigdy „to samo”;
    - "changed": każda inna różnica (zagnieżdżone słowniki i listy przechodzisz, nie porównujesz
      w całości).
    Różnice podawaj w kolejności pól w direct, a potem nadmiarowe pola z mcp.
    "same" ma wartość True tylko wtedy, gdy nie ma różnic. Danych wejściowych nigdy nie modyfikuj.

ZALECANE NARZĘDZIA
    Zwykły Python: prosta funkcja rekurencyjna. Przykłady: „Przybornik” w mini_project_5/README.md.

NA KONIEC SPRAWDŹ KOD POLECENIEM
    uv run pytest mini_project_5/tests/test_step2_compare_call.py -v
"""


def compare_call(direct, mcp) -> dict:
    # TODO: twój kod – zobacz CEL, WYNIK i WYMAGANIA na początku pliku
    raise NotImplementedError("TODO: compare_call")
