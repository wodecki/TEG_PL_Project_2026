# Miniprojekt 3: workflow decyzyjny

**Cel:** zbudować asystenta prowadzącego rozmowę i obsługującego przepływ pracy (ang. workflow). Reguły polityki rabatowej są zapisane w kodzie, a złożony wniosek wymaga zgody właściwych osób.
**Czas:** około 3–3,5 godziny. **Framework:** LangGraph (grafy stanów, pauzy `interrupt()`, mechanizmy zapisu stanu — ang. checkpointers) oraz odpowiedzi w ustalonym schemacie (ang. structured output) z LangChain.

## Kryteria ukończenia

- [ ] `uv run python mini_project_3/src/check.py` pokazuje **PASS** w każdym wierszu (klucz API nie jest potrzebny)
- [ ] `uv run python mini_project_3/src/run_dialogues.py` wypisał ocenę dialogów z twoim LLM-em, etap po etapie (około 1,7 centa z referencyjnym LLM-em)
- [ ] [CONCEPTS.md](CONCEPTS.md) przeczytany, test z Miniprojektu 3 na platformie Edux zaliczony

**Zanim zaczniesz:** Miniprojekt 3 korzysta z twojego kodu z Miniprojektów 1 i 2: twojego LLM-a, wyszukiwania kontekstowego i funkcji `answer_question`. Jeśli któraś z tych części nie jest gotowa, skopiuj opublikowane wzorcowe pliki `step`: patrz „Zostajesz w tyle?” w głównym [README](../README.md#zostajesz-w-tyle). `check.py` powie, jeśli czegoś brakuje.

## Co jest w tym folderze

```
mini_project_3/
  README.md      <- jesteś tutaj
  CONCEPTS.md    teoria do testu
  src/
    step1_required_approvers.py   <- te pięć piszesz ty
    step2_understand_turn.py
    step3_conversation_graph.py
    step4_copilot_graph.py
    step5_score_transcript.py
    check.py                      <- te uruchamiasz
    run_dialogues.py
    chat.py                       (opcjonalnie)
  tests/         testy, które sprawdzają twoje kroki (i odtwarzają dialogi wzorcowe)
  output/        powstaje, gdy uruchomisz programy
```

## Jak pracować

Każde polecenie uruchamiaj z katalogu głównego repozytorium (tego, w którym znajduje się `config.yaml`). W każdym kroku przeczytaj CEL / WYNIK / WYMAGANIA na początku pliku kroku, napisz kod w miejscu `# TODO`, uruchom test kroku, a potem `check.py`. Testy nigdy nie wywołują LLM-a: używają małej atrapy, która zwraca przygotowane z góry odczytania wiadomości i liczy, ile razy ją wywołano.

## Cztery odrębne zadania

| Kto | Co robi | Gdzie |
|---|---|---|
| LLM | **rozumie** wiadomość: jakiego jest rodzaju, co zmienia i jak ją sformułować, żeby była zrozumiała bez reszty rozmowy | krok 2 |
| twój kod | **wylicza**, czego wymaga polityka, za każdym razem tak samo | krok 1 |
| workflow | **kontroluje**, czy wniosek może iść dalej: pyta o brakujące dane, potem czeka na akceptacje | kroki 3–4 |
| człowiek | w roli wskazanej przez politykę **decyduje** o jednej, konkretnej wersji wniosku | pauzy (symulowane) |

Każde z tych zadań jest potrzebne. Bezbłędny silnik reguł nie naprawi źle odczytanej wiadomości, a pauza to jeszcze nie zgoda.

## Polityka rabatowa jako kod (kursowa interpretacja `course-v1`)

POL-001 podaje tabelę przedziałów akceptacji, minimalną marżę i trzy wyjątki. Nie mówi jednak, co się dzieje, gdy te reguły się nakładają. Na potrzeby kursu fikcyjna firma przyjmuje poniższą interpretację, zapisaną w `config.yaml` w sekcji `policy`:

1. **Zwykły przedział:** do 5% zatwierdza przedstawiciel handlowy; powyżej 5% do 12% regionalny kierownik sprzedaży; powyżej 12% do 20% dyrektor handlowy; powyżej 20% CEO **i** CFO.
2. **Wyjątki,** każdy tylko do swojego limitu:
   - wyprzedaż końcówek: regionalny kierownik sprzedaży do 35%;
   - klient strategiczny: dyrektor handlowy do 25%;
   - udokumentowana oferta konkurencji: regionalny kierownik sprzedaży do 15%.

   Wyjątek może obniżyć poziom uprawnień, ale nigdy go nie podniesie.
3. **Wybierany jest najniższy uprawniony poziom.** Firma świadomie wybrała to liberalne rozwiązanie; bardziej rygorystyczna mogłaby wybrać inaczej.
4. **Minimalna marża:** marża po rabacie **poniżej** 9% **dodaje** CFO, z wyjątkiem wyprzedaży końcówek. Wyprzedaż końcówek jest zwolniona z minimalnej marży także powyżej 35%.

| Wniosek | Zatwierdzają |
|---|---|
| 3%, klient strategiczny, marża 10% | Przedstawiciel handlowy |
| 22%, zwykły, marża 10% | CEO i CFO |
| 22%, klient strategiczny, marża 7% | Dyrektor handlowy i CFO |
| 14%, klient strategiczny + oferta konkurencji, marża 7% | Regionalny kierownik sprzedaży i CFO |
| 30%, wyprzedaż końcówek, marża 4% | Regionalny kierownik sprzedaży |
| 36%, wyprzedaż końcówek, marża 4% | CEO i CFO (limit wyprzedaży przekroczony; zwolnienie z minimalnej marży zostaje) |

To konwencja na potrzeby ćwiczenia, a nie tekst polityki. Każde przełożenie polityki na kod wymaga zapisania takiej interpretacji i przetestowania jej.

## Workflow

```
            ┌── document_question ── answer_documents (Miniprojekt 2) ───────────────┐
message ──> understand ── policy_question ── answer_policy (tylko informacja) ─────────┤
            ├── other / error ── krótka odpowiedź ─────────────────────────────────────┤──> koniec tury
            └── approval_request ── update_request ─┬─(brak marży)─> clarify ⟲ ──────┐  │
                                                    └─────────────────> decide <──────┘  │
                                                                          └─> approve ⟲ ─┘
```

`clarify` i `approve` **zatrzymują** graf (`interrupt()`). Program wznawia go odpowiedzią (`Command(resume=…)`): liczbą przy pytaniu o marżę, a przy akceptacji jedną z trzech decyzji, osobno dla każdej roli. Sam graf dostaje zawsze liczbę albo `cancel` przy marży oraz `approved` / `rejected` / `cancel` przy akceptacji. Człowiek może odpowiadać po polsku: `chat.py` przyjmuje marżę zapisaną jako „7,5” albo „7.5” oraz słowa „zatwierdź”, „odrzuć” i „anuluj” (angielskie słowa też działają), a gotowa funkcja `human_answer` z `helpers/text_pl.py` przekształca odpowiedź na liczbę lub odpowiednią wartość `approved` / `rejected` / `cancel`, zanim przekaże ją do grafu. Każda inna odpowiedź (np. „może”) jest nieprawidłowa: graf pyta tę samą rolę jeszcze raz. Zmieniony wniosek dostaje nową **wersję** (ang. revision), a wcześniejsze akceptacje przestają się liczyć. Dopóki graf jest zatrzymany, programy przyjmują tylko odpowiedź na bieżące pytanie, a nową wiadomość odrzucają. Żeby zmienić warunki, anuluj wniosek i złóż go ponownie.

**Ponowne złożenie wniosku.** Zmienione warunki → nowa wersja, którą trzeba zatwierdzić od nowa. Te same warunki po odrzuceniu albo anulowaniu → nowa runda akceptacji od pierwszej roli. Te same warunki po pełnej akceptacji → odpowiedź „Już zatwierdzone”, bez nowej pauzy. „Zatwierdzone” zawsze oznacza, że zatwierdziła **każda** wymagana rola. Jeśli z wniosku o akceptację nie wynika, czy jest nowy, czy zmienia obecny, copilot dopytuje i niczego nie zmienia. Doprecyzowana marża trafia do rozmowy jako twoja wiadomość („Marża po rabacie: 7%”), więc późniejsze pytania („przy tej samej marży”) mogą z niej korzystać.

Statusy: `answered`, `pending_clarification`, `pending_approval`, `approved` (symulowany), `rejected`, `cancelled`, `error`. **Poza zakresem tego miniprojektu:** zapis w CRM-ie, obietnice wobec klienta, sprawdzanie, kim naprawdę są osoby zatwierdzające.

<details>
<summary>Nie możesz uruchomić projektu? Zobacz przebieg referencyjny</summary>

`run_dialogues.py` z referencyjnym LLM-em. Odpowiedzi osób zatwierdzających są symulowane zgodnie ze scenariuszem. Wynik różni się trochę przy każdym uruchomieniu; ten przebieg zapisano razem z jego identyfikatorem:

<!-- reference-run:dialogues (generated by instructor/reference_run.py; do not edit) -->
```
=== Dialogi Miniprojektu 3: openai / gpt-5.4-mini, polityka course-v1 (przebieg 20261006T212757-fe6041ef) ===
Etap                              trafne/ocenione
1 kierowanie (rodzaj wiadomości)  13/13
2 pola odczytane przez LLM        11/11
3 stan wniosku po aktualizacji    8/8
4 osoby zatwierdzające (polityka) 11/11
5 pauzy (typ, rola, kolejność)    13/13
6 status końcowy                  13/13
błędy (nieudane tury)             0

Tura po turze (etapy z błędem):
  D1  policy_question   answered         ok                     Kto zatwierdza rabat 15% dla zwykłego klienta?
  D1  policy_question   answered         ok                     A 22%?
  D1  policy_question   answered         ok                     Kto zatwierdza 3% dla klienta strategicznego prz
  D2  approval_request  approved         ok                     Prześlij do akceptacji rabat 14% na wodę dla Bie
  D2  approval_request  rejected         ok                     Jednak zróbmy 22%, marża bez zmian.
  D3  approval_request  approved         ok                     Prześlij do akceptacji rabat 8% na chipsy dla De
  D4  approval_request  approved         ok                     Prześlij do akceptacji rabat 30% na jogurt z wyp
  D4  approval_request  cancelled        ok                     Nowe zamówienie – 30% rabatu na wodę niegazowaną
  D5  approval_request  approved         ok                     Prześlij do akceptacji rabat 22% dla naszego kli
  D6  approval_request  rejected         ok                     Prześlij do akceptacji 14% dla klienta strategic
  D7  document_question answered         ok                     Co komitet cenowy postanowił w sprawie cen wody 
  D7  other             answered         ok                     Dzięki!
  D8  approval_request  approved         ok                     Prześlij do akceptacji rabat 36% na jogurt z wyp
```
<!-- /reference-run:dialogues -->

`check.py` odtwarza te same dialogi z *idealnym* zrozumieniem wiadomości (bez LLM-a), więc workflow, stan wniosku i politykę da się sprawdzić osobno. Jeśli przebieg na żywo wypada gorzej niż odtworzenie, zwykle zawodzi zrozumienie wiadomości, ale sprawdź konkretne tury: przebieg na żywo także oblicza embeddingi pytań i generuje odpowiedzi na bieżąco. W naszym przebiegu z referencyjnym LLM-em wszystkie sprawdzenia na każdym etapie zakończyły się wynikiem poprawnym, bez żadnej nieudanej tury. Pierwsza, prostsza wersja promptu (jeszcze w angielskiej edycji kursu) traktowała podziękowanie „Thanks!” jak pytanie i przepisywała je na poprzednie pytanie (zob. CONCEPTS.md).
</details>

## Ile to kosztuje

| Program | Wywołania | Koszt z referencyjnym LLM-em |
|---|---|---|
| `check.py` | żadnych | bezpłatnie |
| `run_dialogues.py` | 13 wywołań „understand”, 1 odpowiedź na pytanie o dokumenty, 1 embedding na żywo | około 1,7 centa za przebieg (w naszym przebiegu zmierzono 1,65 centa) |
| `chat.py` (opcjonalnie) | 1 wywołanie na wiadomość | ułamek centa za wiadomość |

Embeddingi pytań o dokumenty, przekształconych w pytania samodzielne, są obliczane **na bieżąco przez OpenAI** i nie są zapisywane w pamięci podręcznej kursu (ang. cache). Dlatego `run_dialogues.py` i `chat.py` potrzebują `OPENAI_API_KEY`, nawet jeśli twój LLM pochodzi od innego dostawcy. Z innym LLM-em workflow działa, o ile model obsługuje structured output; źle odczytane wiadomości widać w ocenach etapów.

---

## Przybornik

Przykłady na fikcyjnych danych służą poznaniu narzędzi; **nie** są rozwiązaniem zadania.

### Krok 1: reguły jako dane

```python
policy = {"bands": [{"up_to": 10, "roles": ["Kierownik zespołu"]}, {"up_to": 100, "roles": ["Dyrektor"]}]}
rank = next(i for i, band in enumerate(policy["bands"]) if 7 <= band["up_to"])   # 0: pierwszy pasujący przedział
import math; math.isfinite(float("nan"))                                           # False: odrzuć taką wartość
raise ValueError("kwota musi być liczbą od 0 do 100, otrzymano 140")
```

### Krok 2: odpowiedź w ustalonym schemacie, kontekst rozmowy i kopia modelu

```python
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
messages = [SystemMessage("Sklasyfikuj wiadomość."), HumanMessage("Zarezerwuj salę"), AIMessage("Gotowe."), HumanMessage("A taksówkę?")]
llm.with_structured_output(MySchema).invoke(messages)

ticket = Ticket(revision=1, seats=2)
ticket.model_copy(update={"seats": 3, "revision": 2})      # nowy obiekt; stary się nie zmienia
```

### Kroki 3–4: graf z krawędzią warunkową, pętlą i pauzą

```python
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import interrupt, Command

def ask_size(state):
    size = interrupt({"type": "question", "text": "Jaki rozmiar?"})   # tu graf się zatrzymuje; zwraca wartość wznowienia
    return {"size": size}

graph = StateGraph(OrderState)
graph.add_node("classify", classify)
graph.add_node("ask_size", ask_size)
graph.add_edge(START, "classify")
graph.add_conditional_edges("classify", lambda s: "ask_size" if s.get("size") is None else END, ["ask_size", END])
graph.add_conditional_edges("ask_size", lambda s: END if s.get("size") else "ask_size", ["ask_size", END])  # pętla do skutku
app = graph.compile(checkpointer=MemorySaver())          # pauza wymaga checkpointera

cfg = {"configurable": {"thread_id": "klient-7"}}        # jedna rozmowa = jeden wątek
out = app.invoke({"messages": [...]}, cfg)
out["__interrupt__"][0].value                              # {'type': 'question', 'text': 'Jaki rozmiar?'}
app.invoke(Command(resume="L"), cfg)                       # dalej: ask_size uruchamia się PONOWNIE od początku
app.get_state(cfg).values                                  # stan tego wątku
```

---

## Jeśli utkniesz

<details>
<summary>Krok 4: „zrozumienie wykonało się ponownie” / LLM jest wywoływany dwa razy</summary>

Przy wznowieniu LangGraph uruchamia zatrzymany węzeł **od początku**. Umieść wywołanie LLM-a w osobnym węźle (`understand`), przed węzłami z pauzami, a przed `interrupt()` umieszczaj tylko proste operacje, które można bezpiecznie powtórzyć.
</details>

<details>
<summary>Krok 4: „Cannot use Command(resume=...) without checkpointer”</summary>

Bez checkpointera graf i tak zatrzyma się na `interrupt()`, ale nic nie zostanie zapisane, więc nie ma czego wznawiać. Skompiluj graf z podanym checkpointerem i wznawiaj go z tym samym `thread_id`.
</details>

<details>
<summary>Krok 3: pytanie o politykę zmieniło wniosek</summary>

Pytania o politykę to tylko informacja. Zbuduj z tury tymczasowy `DiscountRequest` i nie zapisuj go w `state["request"]`.
</details>

<details>
<summary>Krok 1: jeden z przypadków sprawdzonych ręcznie się nie zgadza</summary>

Sprawdź kolejność: przedział → wyjątki, które mają zastosowanie (flaga **i** rabat nie wyższy niż limit) → najniższy poziom uprawnień → minimalna marża (poniżej 9%, nie dla wyprzedaży końcówek). Marża równa 9% nie jest poniżej minimalnej, a rabat 35% na wyprzedaż końcówek nadal korzysta z wyjątku.
</details>

## Ustalone wartości (są już w `config.yaml`, nie zmieniaj ich)

| Ustawienie | Wartość |
|---|---|
| Polityka | `policy`: bands, exceptions, `margin_floor: 9`, `floor_role: CFO`, `version: course-v1` |
| Prompt „understand” | `prompts.understand_system` |
| Dialogi | `data/eval/mini_project_3_dialogues.yaml`: 8 dialogów, 13 tur użytkownika, wzorzec sprawdzony ręcznie |
| Referencyjny LLM | `openai` / `gpt-5.4-mini` |
