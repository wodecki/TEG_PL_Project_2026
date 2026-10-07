# Miniprojekt 5: jeden standardowy interfejs i końcowy asystent

**Cel:** udostępnić narzędzia Kovalo przez standardowy protokół MCP (ang. Model Context Protocol) i zintegrować je w końcowym asystencie. W jednej rozmowie asystent odpowiada na pytania o dokumenty i dane firmy, stosuje reguły polityki rabatowej oraz wstrzymuje realizację wniosku do czasu decyzji osób uprawnionych do jego zatwierdzenia.
**Czas:** około 3–3,5 godziny. **Framework:** zestaw narzędzi programistycznych MCP dla Pythona (ang. SDK), w tym `FastMCP` i komunikacja przez standardowe wejście i wyjście (stdio), oraz LangGraph.

## Kryteria ukończenia

- [ ] `uv run python mini_project_5/src/check.py` pokazuje **PASS** w każdym wierszu (klucz API nie jest potrzebny)
- [ ] `uv run python mini_project_5/src/run_agent_mcp.py` zadał pytania z Miniprojektu 4 agentowi korzystającemu z MCP (około 3,9 centa z referencyjnym LLM-em)
- [ ] `uv run python mini_project_5/src/run_assistant_eval.py` ocenił całego asystenta (około 4,4 centa z referencyjnym LLM-em)
- [ ] [CONCEPTS.md](CONCEPTS.md) przeczytany, test z Miniprojektu 5 na platformie Edux zaliczony

**Zanim zaczniesz:** Miniprojekt 5 korzysta z twojego kodu z Miniprojektów 1–4: wyszukiwania, grafu copilota oraz narzędzi agenta i funkcji oceniającej. Jeśli któraś z tych części nie jest gotowa, skopiuj opublikowane wzorcowe pliki `step`: patrz „Zostajesz w tyle?” w głównym [README](../README.md#zostajesz-w-tyle). `check.py` powie, czego brakuje.

## Co jest w tym folderze

```
mini_project_5/
  README.md      <- jesteś tutaj
  CONCEPTS.md    teoria do testu
  src/
    step1_build_server.py        <- te cztery piszesz ty
    step2_compare_call.py
    step3_answer_with_tools.py
    step4_build_assistant.py
    check.py                     <- te uruchamiasz
    run_agent_mcp.py
    run_assistant_eval.py
    serve.py                     program serwera (klienci uruchamiają go za ciebie)
    show_mcp.py                  (opcjonalnie) co oferuje serwer
    chat.py                      (opcjonalnie) końcowy asystent
  tests/         testy, które sprawdzają twoje kroki (i serwery testowe symulujące błędy)
  output/        powstaje, gdy uruchomisz programy
```

## Jak pracować

Każde polecenie uruchamiaj z katalogu głównego repozytorium (tego, w którym jest `config.yaml`). Przy każdym kroku przeczytaj CEL / WYNIK / WYMAGANIA na początku pliku kroku, napisz kod w miejscu `# TODO`, uruchom test kroku, a potem `check.py`. Testy nigdy nie wywołują LLM-a i nie potrzebują klucza: łączą się z twoim serwerem w pamięci, a działanie LLM-a symuluje model realizujący przygotowany scenariusz.

## Schemat

```
 Klienci MCP, z których każdy uruchamia WŁASNY lokalny proces serwera (stdio):
   nasz asystent   |   MCP Inspector   |   Claude Desktop   ...
        │  komunikaty JSON-RPC przez stdin/stdout serwera
 Serwer MCP Kovalo (krok 1): sześć narzędzi z Miniprojektu 4, tylko do odczytu + dokumenty + prompt
        │  cienkie nakładki
 Funkcje i rekordy z Miniprojektu 4  ←  indeks z Miniprojektu 2, reguły z Miniprojektu 3

 Asystent (krok 4) = graf copilota z Miniprojektu 3 z JEDNYM podmienionym węzłem:
   understand ─┬─ document_question ─> answer_with_tools  (krok 3: agent, narzędzia przez MCP)
               ├─ policy_question   ─> reguły z MP3 (bez wywołania narzędzia)
               ├─ approval_request  ─> wniosek, doprecyzowanie i pauzy na akceptację z MP3
               └─ other / error     ─> odpowiedzi z MP3
```

**Jedna implementacja serwera, wielu klientów.** Przy stdio każdy klient uruchamia własną kopię serwera jako podproces: to standardowy interfejs, a nie wspólna usługa. Akceptacje nie są narzędziem serwera: zostają w asystencie, gdzie decyduje człowiek.

**Jeden właściciel rozmowy.** Każdą wiadomość interpretuje jednokrotnie węzeł `understand` z Miniprojektu 3. Podmiana węzła zmienia tylko to, co *odpowiada* na pytanie o dokumenty lub dane, nic więcej. Prompt rozumienia z Miniprojektu 5 kieruje do agenta także pytania o dane firmy (OTIF, faktury, kary umowne) i traktuje ponowne przesłanie wniosku („prześlij to”, „spróbuj jeszcze raz”) jako aktualizację. Drugą zasadę wprowadzono po wykryciu błędu podczas ewaluacji: zob. przebieg referencyjny. Pauzy w `chat.py` przyjmują odpowiedzi po polsku, tak jak w Miniprojekcie 3: `zatwierdź` / `odrzuć` / `anuluj`, a liczby z przecinkiem dziesiętnym („7,5”).

## Co jest gotowe (tego nie piszesz)

| Gotowy element | Co gwarantuje |
|---|---|
| `helpers/mcp_runtime.py` | połączenie: pętlę zdarzeń w tle, dzięki której twój kod zostaje synchroniczny; limity czasu na start, na każde wywołanie i na zwalnianie zasobów; wywołanie po przekroczeniu limitu jest anulowane, a połączenie nigdy nie jest używane ponownie; zamykanie trwa ograniczony czas (SDK zamyka stdin, czeka, kończy proces, a w ostateczności wymusza jego zakończenie); **zgodność każdego wyniku z rekordem z Miniprojektu 4 jest sprawdzana, zanim cokolwiek uzupełni wartości domyślne** |
| `helpers/assistant.py` | `replace_node` (podmiana węzła), `assistant_config` (prompt z MP5, na kopii konfiguracji), `assistant_turn` (jedyny punkt wejścia: zachowuje strażnika z Miniprojektu 3 „żadnej nowej wiadomości w trakcie pauzy” i uruchamia na jednym połączeniu tylko jedną turę naraz); miejsce, w którym przechowywany jest zapis przebiegu (ang. trace) agenta |
| `helpers/assistant_eval.py` | ocenę każdej tury według jej oczekiwanej ścieżki |
| `mini_project_5/src/serve.py` | program serwera; indeks wyszukiwania powstaje przy pierwszym wyszukiwaniu |

**Dlaczego nie `load_mcp_tools`?** Demo MCP z kursu zamienia narzędzia sesji na narzędzia LangChaina funkcją `langchain_mcp_adapters.tools.load_mcp_tools(session)`. To działa, ale wersja adaptera zgodna z przypiętą wersją LangChaina przekazuje modelowi tylko tekst wyniku i pomija `structuredContent`. Nasz zapis przebiegu potrzebuje ustrukturyzowanego rekordu, sprawdzonego przed jakimkolwiek dalszym przetwarzaniem. Dlatego `connection.tools()` robi to samo bezpośrednio na MCP SDK: buduje narzędzia z `session.list_tools()` i wywołuje `session.call_tool()`. Zachowuje surowy wynik i sprawdza jego zgodność z rekordem z Miniprojektu 4.

**Cztery sposoby, w jakie wywołanie może się nie udać**; każdy komunikat błędu podaje warstwę:
- `[błąd narzędzia]` (warstwa `tool`): serwer odpowiedział z `isError: true`;
- `[błąd protokołu]` (`protocol`): przyszedł obiekt błędu JSON-RPC;
- `[błąd transportu]` (`transport`): odpowiedzi nie ma, bo serwer się zakończył, potok się zerwał albo minął limit czasu wywołania;
- `[błąd walidacji lokalnej]` (`validation`): odpowiedź nadeszła, ale łamie kontrakt rekordu.

„Brak danych za październik” nie jest żadnym z nich, tylko zwykłym wynikiem.

<details>
<summary>Nie możesz uruchomić projektu? Zobacz przebiegi referencyjne</summary>

Dziewięć pytań z Miniprojektu 4 zadanych agentowi, który korzysta z narzędzi przez MCP:

<!-- reference-run:agent_mcp_run (generated by instructor/reference_run.py; do not edit) -->
```
=== Miniprojekt 4, jeden agent przez MCP: openai / gpt-5.4-mini, polityka course-v1, warunki terms-v1 (przebieg 20261006T213648-aa9ccf1b) ===
Test (co mierzy)                                   wynik
1 pokrycie narzędzi: każde potrzebne wywołanie     9/9 pytań
2 poprawne argumenty (gdzie liczono karę)          3/3 pytań
3 fakty: każdy kluczowy fakt w odpowiedzi          8/9 pytań
4 pokrycie liczb źródłami: liczby bez źródła       0 (podane przez użytkownika, osobno: 1)
5 twierdzenia o zatwierdzeniu w odpowiedziach      0/9 odpowiedzi
wyniki przebiegów                                  9 answered, 0 error, 0 limit
wywołania narzędzi                                 21 (nieudane: 0)
tokeny                                             40 931 wejściowych / 1867 wyjściowych; około 3,9 centa

Według pytań (narzędzia = spełnione potrzeby; argumenty; fakty; liczby bez źródła):
  P1  answered narzędzia 100%  argumenty ok     fakty 100%  bez źródła: brak
      Kara wynosi **7296,00 PLN**.  Źródła: - umowa **CON-101**: cel OTIF **97,0%**, klauzula kary **tak**, stawka **2,0%** za każdy pełny punkt procentowy 
  P2  answered narzędzia 100%  argumenty ok     fakty 100%  bez źródła: brak
      Kara za OTIF za czerwiec 2026 r. wynosi **362 400 groszy, czyli 3 624,00 PLN**.  Źródła: - **Umowa**: `CON-101` — jest klauzula kary umownej, cel OTIF
  P3  answered narzędzia 100%  argumenty ok     fakty 100%  bez źródła: brak
      Nie. Dla maja 2026 r. kara za OTIF **nie nalicza się**, bo:  - umowa z Mleczną Doliną ma klauzulę kary umownej: **tak**; źródło: **CON-101** - cel OTI
  T1  answered narzędzia 100%  argumenty -      fakty   0%  bez źródła: brak
      Tak — na koniec września 2026 r. Kovalo może rozwiązać umowę z 60-dniowym okresem wypowiedzenia, bo OTIF przez trzy kolejne miesiące był poniżej 94%: 
  A1  answered narzędzia 100%  argumenty -      fakty 100%  bez źródła: brak
      W lipcu 2026 r. Aqua Kryształ **nie osiągnął celu OTIF**: OTIF wyniósł **95,1%** przy celu **96,0%**. Źródło: **CON-102** oraz dane firmy dla **SUP-20
  D1  answered narzędzia 100%  argumenty -      fakty 100%  bez źródła: brak
      Musi zatwierdzić **Dyrektor handlowy i CFO**.  Uzasadnienie: rabat **22%** wpada w wyjątek dla **klienta strategicznego** do **25%**, ale marża po rab
  S1  answered narzędzia 100%  argumenty -      fakty 100%  bez źródła: brak
      Umowa z TransBałtem wymaga, aby **98% palet było dostarczanych w uzgodnionym oknie czasowym**.   Źródło: **CON-103**.  Dodatkowo w umowie są podane st
  N1  answered narzędzia 100%  argumenty -      fakty 100%  bez źródła: brak
      Brak danych o OTIF Mlecznej Doliny za 2026-10. Źródło: dane firmy dla SUP-114.
  B1  answered narzędzia 100%  argumenty -      fakty 100%  bez źródła: brak
      Wymagana akceptacja: **Dyrektor handlowy**.  Uzasadnienie: rabat **14%** mieści się w przedziale do **20%** według **POL-001**; marża po rabacie **10%
```
<!-- /reference-run:agent_mcp_run -->

Wynik niemal pokrywa się z przebiegiem Miniprojektu 4 na bezpośrednich narzędziach: argumenty 3/3, fakty 8/9, żadnej liczby bez źródła, żadnego twierdzenia o zatwierdzeniu. Pokrycie narzędzi jest wyższe (9/9 wobec 8/9), bo tym razem agent pobrał w T1 także OTIF za lipiec. To jeden przebieg, więc nie przypisuj tej różnicy transportowi. W T1 agent i tak odpowiedział „Tak”: zaliczył lipcowe 94,6% do miesięcy „poniżej 94%”. Transport nie zmienia rozumowania agenta, a pobranie właściwych danych nie gwarantuje właściwego wniosku.

Cały asystent, oceniony według oczekiwanej ścieżki każdej tury (5 rozmów z Miniprojektu 5 + 8 dialogów z Miniprojektu 3):

<!-- reference-run:assistant_run (generated by instructor/reference_run.py; do not edit) -->
```
=== Asystent z Miniprojektu 5: openai / gpt-5.4-mini, przez MCP (przebieg 20261006T213833-2ffa23b6) ===
Sprawdzenie (gdy definiuje je oczekiwana ścieżka)    trafne/ocenione
ścieżka (oczekiwany kind)                            25/25
status końcowy                                       25/25
pola wyodrębnione przez LLM                          11/11
pauzy (rodzaj, rola, kolejność)                      22/22
osoby zatwierdzające (polityka)                      19/19
stan wniosku                                         15/15
zapis przebiegu agenta tylko tam, gdzie oczekiwany   25/25
pytania o dane: każde potrzebne wywołanie            4/4
pytania o dane: argumenty obliczenia                 1/1
pytania o dane: każdy kluczowy fakt                  4/4
pytania o dane: żadnej liczby bez pokrycia           4/4
pytania o dane: brak twierdzenia o akceptacji        4/4
wywołania MCP (nieudane)                             7 (0)
tokeny (rozumienie + agent)                          41 993 wejściowych / 2866 wyjściowych; około 4,4 centa

Tura po turze (sprawdzenia, które nie przeszły):
  C1  document_question answered         ok                             Ile wynosi kara, którą Mleczna Dolina jest w
  C1  approval_request  approved         ok                             Teraz prześlij do akceptacji rabat 14% na wo
  C1  document_question answered         ok                             A jaki był OTIF dostawcy Aqua Kryształ w lip
  C1  approval_request  approved         ok                             Prześlij jeszcze raz ten sam rabat dla Biedr
  C2  policy_question   answered         ok                             Kto musi zatwierdzić rabat 22% dla naszego k
  C2  approval_request  approved         ok                             Prześlij to.
  C3  approval_request  rejected         ok                             Zatwierdź rabat 14% na wodę niegazowaną dla 
  C3  approval_request  approved         ok                             Spróbuj jeszcze raz na tych samych warunkach
  C4  approval_request  approved         ok                             Prześlij do akceptacji rabat 8% na chipsy dl
  C4  policy_question   answered         ok                             Przy tej samej marży kto zatwierdziłby 12%?
  C5  document_question answered         ok                             Jaki był OTIF Mlecznej Doliny w październiku
  C5  other             answered         ok                             Dzięki!
  D1  policy_question   answered         ok                             Kto zatwierdza rabat 15% dla zwykłego klient
  D1  policy_question   answered         ok                             A 22%?
  D1  policy_question   answered         ok                             Kto zatwierdza 3% dla klienta strategicznego
  D2  approval_request  approved         ok                             Prześlij do akceptacji rabat 14% na wodę dla
  D2  approval_request  rejected         ok                             Jednak zróbmy 22%, marża bez zmian.
  D3  approval_request  approved         ok                             Prześlij do akceptacji rabat 8% na chipsy dl
  D4  approval_request  approved         ok                             Prześlij do akceptacji rabat 30% na jogurt z
  D4  approval_request  cancelled        ok                             Nowe zamówienie – 30% rabatu na wodę niegazo
  D5  approval_request  approved         ok                             Prześlij do akceptacji rabat 22% dla naszego
  D6  approval_request  rejected         ok                             Prześlij do akceptacji 14% dla klienta strat
  D7  document_question answered         ok                             Co komitet cenowy postanowił w sprawie cen w
  D7  other             answered         ok                             Dzięki!
  D8  approval_request  approved         ok                             Prześlij do akceptacji rabat 36% na jogurt z
```
<!-- /reference-run:assistant_run -->

**Błąd wykryty w ewaluacji i poprawiony w prompcie MP5.** W dwóch pierwszych przebiegach angielskiej wersji projektu wiadomości „Submit that.” (po pytaniu o politykę) i „Please try again with the same terms.” (po odrzuceniu) zostały zrozumiane jako wnioski o akceptację, które nie były ani nowe, ani aktualizacją. Reguła z Miniprojektu 3 słusznie dopytała wtedy „nowy wniosek czy zmiana?”, a tura kończyła się błędem. Dlatego prompt rozumienia w MP5 mówi, że ponowne przesłanie to aktualizacja. W naszym przebiegu na polskich danych, z tym promptem od początku, „Prześlij to.” (C2) i „Spróbuj jeszcze raz na tych samych warunkach.” (C3) zostały rozpoznane jako aktualizacje (`update`), a wszystkie 25 tur przeszło każde sprawdzenie. Jest to wynik jednego przebiegu na niewielkim zestawie edukacyjnym, a nie gwarancja poprawności we wszystkich sytuacjach.
</details>

## Ile to kosztuje

| Program | Wywołania | Koszt z referencyjnym LLM-em |
|---|---|---|
| `check.py`, `show_mcp.py` | żadnych | bezpłatnie |
| `run_agent_mcp.py` | 9 pytań, około 21 wywołań MCP | około 3,9 centa (zmierzone: 40 931 + 1867 tokenów) |
| `run_assistant_eval.py` | 25 tur: 25 razy rozumienie wiadomości, 4 odpowiedzi agenta, 7 wywołań MCP | około 4,4 centa (zmierzone: 41 993 + 2866 tokenów) |
| `chat.py` (opcjonalnie) | za każdą wiadomość | ułamek centa |

**Dwa miejsca z kluczami.** *Serwer* oblicza na bieżąco wektorowe reprezentacje zapytań (ang. embeddings) przez OpenAI. Sam czyta `OPENAI_API_KEY` z pliku `.env` projektu i robi to dopiero przy pierwszym wyszukiwaniu. *Asystent* potrzebuje klucza do twojego LLM-a. Żaden klucz nigdy nie trafia do argumentów ani wyników narzędzia.

## Serwer w innym kliencie

Ta część jest opcjonalna. Polecenie, którego potrzebuje każdy klient MCP (z katalogu głównego repozytorium):

```
uv run python mini_project_5/src/serve.py --config config.yaml
```

- **MCP Inspector:** `npx @modelcontextprotocol/inspector uv run python mini_project_5/src/serve.py --config config.yaml`
- **Claude Desktop:** dopisz do `claude_desktop_config.json` (ze swoimi ścieżkami bezwzględnymi):

```json
{"mcpServers": {"kovalo": {"command": "uv",
  "args": ["--directory", "/ABSOLUTE/PATH/TO/REPO", "run", "python", "mini_project_5/src/serve.py", "--config", "config.yaml"]}}}
```

Inni klienci widzą sześć narzędzi tylko do odczytu, dokumenty i prompt, ale nie workflow akceptacji: ten zostaje w naszym asystencie.

---

## Przybornik

Przykłady na fikcyjnych danych służą poznaniu narzędzi; **nie** są rozwiązaniem zadania.

### Krok 1: serwer FastMCP

```python
from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel

class Stock(BaseModel):
    status: str
    units: int | None = None

def build_shop_server(shop) -> FastMCP:
    server = FastMCP("shop")

    @server.tool(annotations={"readOnlyHint": True})
    def get_stock(sku: str) -> Stock:            # TYP zwracany staje się outputSchema
        """Liczba sztuk na stanie dla SKU (np. A-17)."""
        return lookup(shop, sku)                 # shop: z domknięcia, nigdy z argumentu

    @server.resource("shop://products/{sku}")
    def product(sku: str) -> str:
        if sku not in shop.catalogue:            # dokładny identyfikator, nigdy wzorzec pliku ani ścieżka
            raise ValueError(f"nieznany produkt {sku!r}")
        return shop.catalogue[sku]

    @server.prompt()
    def restock_review(sku: str) -> str:
        return f"Oceń, czy uzupełnić zapas {sku}."
    return server
```

### Krok 2: porównywanie dwóch rekordów pole po polu

```python
def walk(a, b, path=""):
    if isinstance(a, dict) and isinstance(b, dict):
        for key in a: ...                       # brak w b? schodź głębiej z f"{path}.{key}"
    elif isinstance(a, list) and isinstance(b, list):
        for i in range(max(len(a), len(b))): ...  # ścieżki w rodzaju "items[2].qty"
type(97) is type(97.0)                           # False: reprezentacja JSON jest inna
```

### Kroki 3–4: agent jako węzeł i gotowe funkcje pomocnicze

```python
agent = create_agent(llm, tools, system_prompt="...")        # langchain.agents; zbuduj go raz
def node(state):
    trace = run_question(agent, state["turn"].standalone, Budget.from_config(config))
    return {"messages": [AIMessage(trace.answer or "...")], "record": agent_trace_envelope(trace), ...}

graph = replace_node(original_graph, "some_node", node, MemorySaver())   # ten sam graf, jeden węzeł podmieniony
```

---

## Jeśli utkniesz

<details>
<summary>Krok 1: narzędzie nie ma outputSchema / structuredContent to None</summary>

Dodaj adnotację typu zwracanego z klasą rekordu (`-> OtifResult`). Funkcja z adnotacją `-> dict` nie publikuje schematu wyniku, więc klient dostaje tylko tekst.
</details>

<details>
<summary>„[błąd walidacji lokalnej] ...: brak”</summary>

Wynik z serwera nie zawiera wszystkich pól rekordu z Miniprojektu 4. Zwracaj sam rekord, a nie ręcznie utworzony słownik, i nigdy nie usuwaj pola ani nie zmieniaj jego nazwy: decyduje kanoniczny kontrakt, nie własny schemat serwera.
</details>

<details>
<summary>Przebieg na żywo kończy się komunikatem „serwer MCP się nie uruchomił”</summary>

Komunikat zawiera ostatnie wiersze stderr serwera. Najczęściej któryś krok nie jest jeszcze napisany albo ścieżka do pliku konfiguracji jest błędna. Uruchom `uv run python mini_project_5/src/show_mcp.py`.
</details>

<details>
<summary>Krok 4: „modelowi ze skryptem skończyły się obiekty Turn: dodatkowe wywołanie rozumienia?”</summary>

Coś uruchamia rozumienie dwa razy dla jednej wiadomości. Nie dodawaj komponentu kierującego wiadomości przed grafem z Miniprojektu 3: podmień tylko węzeł, który odpowiada (`replace_node`), i zawsze przechodź przez `assistant_turn`.
</details>

## Ustalone wartości (są już w `config.yaml`, nie zmieniaj ich)

| Ustawienie | Wartość |
|---|---|
| Prompt rozumienia | `prompts.assistant_understand_system` (prompt z Miniprojektu 3 uzupełniony o dane firmy i ponowne przesłanie wniosku) |
| Limity czasu połączenia | `mcp`: `startup_timeout_s: 60`, `call_timeout_s: 120`, `cleanup_timeout_s: 10` |
| Rozmowy | `data/eval/mini_project_5_conversations.yaml` (5, sprawdzone ręcznie) + 8 dialogów z Miniprojektu 3 |
| Referencyjny LLM | `openai` / `gpt-5.4-mini` |
