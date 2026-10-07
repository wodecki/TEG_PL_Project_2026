# Laboratorium TEG

W tym repozytorium znajdziesz materiały na ćwiczenia z kursu Technologie Generatywne.

W pięciu miniprojektach zbudujesz asystenta sztucznej inteligencji (ang. artificial intelligence, AI) dla menedżerów **Kovalo Distribution**, fikcyjnego polskiego dystrybutora żywności ([scenariusz biznesowy](business_scenario.md)). Skróty i pojęcia biznesowe z dokumentów firmy (CEO, CFO, OTIF, DSO, marża brutto, nota uznaniowa…) wyjaśnia [słownik pojęć biznesowych](slownik.md).

Realizacja tych mini-projektów przygotuje Cię do 5 testów cząstkowych. Testy te zawierają po 10 pytań, korespondujących zarówno z treściami wykładu, jak i zadaniami w mini-projektach. 

Zarówno firma, jak i dane źródłowe (folder `data/`) są fikcyjne. Projekt został opracowany z wykorzystaniem narzędzi i modeli sztucznej inteligencji (Anthropic i OpenAI).

## Od czego zacząć

```bash
uv sync                          # raz: instaluje wszystko, łącznie z Pythonem
cp .env.example .env             # potem wpisz klucz OpenAI (zobacz „Który LLM?”)
uv run python mini_project_1/src/check.py   # pokazuje, co zrobić dalej
```

Program sprawdzający wypisuje PASS albo FAIL przy każdym kroku (`Krok 1`, `Krok 2`…), a na końcu wiersz `SUMMARY: zaliczone sprawdzenia: X/Y`.

Potem otwórz **[mini_project_1/README.md](mini_project_1/README.md)**.

### Na Windowsie

Polecenia z tego projektu działają w **PowerShellu** (albo w Windows Terminal) dokładnie tak, jak są zapisane, łącznie z ukośnikami `/`. Kilka rzeczy wygląda inaczej:

- **Instalacja uv** w PowerShellu: `powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"`, a potem otwórz nowy terminal.
- **Umieść projekt w krótkiej ścieżce poza OneDrive**, np. `C:\dev\kovalo`. Synchronizacja OneDrive potrafi blokować pliki w `.venv`, a bardzo długie ścieżki sprawiają kłopoty.
- **`.env`:** w PowerShellu działa `cp .env.example .env`. W starym wierszu polecenia (cmd) użyj `copy .env.example .env`. Jeśli tworzysz plik w Notatniku, sprawdź, czy nazywa się `.env`, a nie `.env.txt` (włącz „Rozszerzenia nazw plików” w Eksploratorze).
- **Ollama:** zainstaluj ją z [ollama.com](https://ollama.com). Działa w tle (ikona w zasobniku systemowym), więc `ollama serve` nie jest potrzebne.
- **Pierwsze `uv sync` może trwać długo**, bo antywirus skanuje nowe pliki. To normalne.


## Który LLM?

Skrypty wykorzystane w mini-projektach zawierają odwołania do modeli językowych. Osobiście rekomenduję **modele OpenAI: `gpt-5.4-mini` do generowania odpowiedzi i `text-embedding-3-small` do tworzenia wektorowych reprezentacji tekstu (ang. embeddings).** Modele te wykorzystamy zarówno do uruchomień, jak i sprawdzania każdego miniprojektu. W efekcie, potrzebne będą  biblioteka [uv](https://docs.astral.sh/uv/) i klucz API OpenAI (ten sam co w demach z kursu).

Według moich pomiarów z LLM-em referencyjnym uruchomienie na żywo wszystkich opisanych programów z pięciu miniprojektów powinno kosztować nie więcej niż 1 USD. README każdego miniprojektu wymienia jego programy i ich koszt. Całkowity koszt zależy od liczby ponownych uruchomień; przy opisanym sposobie pracy powinien być znacznie niższy niż 5 USD. Przyjęte ceny (cennik OpenAI, październik 2026 r., zapisane na stałe w `config.yaml`): 0,75 USD za milion tokenów wejściowych i 4,50 USD za milion tokenów wyjściowych dla `gpt-5.4-mini`, 0,02 USD za milion tokenów dla embeddingów. Embeddingi, których potrzebujesz, są dołączone do projektu, więc nic nie kosztują.

W naszym porównaniu te same dokumenty po polsku zajmują około 1,6 raza więcej tokenów — jednostek tekstu przetwarzanych przez model — niż ich angielskie odpowiedniki. Przy tej samej cenie za token oznacza to wyższy koszt przetworzenia tych dokumentów. W Miniprojekcie 1 przyjrzysz się temu pomiarowi.

**Dostępne są również dwa inne warianty pracy:**

- **Inny LLM:** OpenRouter albo model na własnym komputerze w Ollamie (za darmo). Miniprojekt 1 pokazuje, jak go podłączyć („Podłącz swój LLM”). Kod obsługuje tych dostawców, ale zgodność z wymaganiami poszczególnych miniprojektów zależy od wybranego modelu. Odpowiedzi, wyniki i koszty będą inne niż nasze. Małe modele lokalne częściej zwracają odpowiedź, której programy nie potrafią odczytać, a programy uruchamiane na żywo o tym przypominają. Kilka opcjonalnych porównań, oznaczonych w README, wymaga OpenAI. Testy jednostkowe nie wywołują LLM-a, więc ich wyniki nie zależą od dostawcy modelu.
- **Bez LLM-a:** każdy quiz da się zaliczyć bez uruchamiania kodu. Przeczytaj README, CONCEPTS.md i przebieg referencyjny każdego miniprojektu; pytania z quizu podają wszystkie potrzebne dane. Zbudowanie projektu to najlepsze przygotowanie, ale nie wymóg.

## Język projektu

Dokumentacja, dane i komunikaty programów są po polsku. Identyfikatory w kodzie, klucze konfiguracji i wartości statusów (np. `answered`, `pending_approval`) zostają po angielsku, a jeden dokument firmy (PL-601) jest celowo po angielsku.

## Foldery

| Folder | Co zawiera | Czy go edytujesz? |
|---|---|---|
| `mini_project_1/` … `mini_project_5/` | jeden folder na miniprojekt: instrukcje, twój kod, testy, program sprawdzający | **tak**: tylko pliki `step` w `src/` |
| `data/` | dokumenty Kovalo, pytania testowe, gotowe embeddingi | nie |
| `helpers/` | wspólny kod, z którego korzystają miniprojekty | nie |
| `config.yaml` | ustawienia projektu | tylko sekcję `llm` (twój LLM, Miniprojekt 1, krok 6) |
| `business_scenario.md`, `slownik.md` | scenariusz biznesowy i słownik pojęć biznesowych | nie |

## Korzystaj z frameworków z kursu

Korzystaj z bibliotek używanych w przykładach z kursu: **LangChain** do obsługi dokumentów, podziału na fragmenty (ang. chunks), tworzenia embeddingów i baz wektorowych (ang. vector stores), a **LangGraph** do definiowania przepływów pracy (ang. workflows) i agentów w miniprojektach 3–4. Gotowe komponenty ograniczają ilość kodu pomocniczego. Pozwalają skupić się na tym, co system ma wyszukiwać, jak oceniać wyniki i jakie decyzje powierzyć agentowi.

Praktyczne zasady:
- Zanim napiszesz pętlę albo parser, sprawdź, czy LangChain nie ma do tego gotowego komponentu: do wczytywania dokumentów (ang. loader), podziału tekstu (ang. splitter), przechowywania wektorów lub wyszukiwania fragmentów (ang. retriever).
- Przekazuj między krokami obiekty `Document` z LangChain (`page_content` + `metadata`), a nie własne struktury danych.
- Opisy na początku plików kroków (ang. docstrings) wskazują, którego komponentu użyć. Przykłady z kursu (`src/3. Retrieval Augmented Generation`, `src/4. Graphs`, `src/5. Tools and Agents`) pokazują każdy z nich w działaniu.

## Pięć miniprojektów

| Miniprojekt | Budujesz | Moduł kursu |
|---|---|---|
| **1** | wyszukiwanie po znaczeniu w dokumentach, szacowanie tokenów i kosztów, podłączenie twojego LLM-a | 1–2 LLM-y, tokeny, embeddingi |
| **2** | odpowiedzi z odwołaniami do źródeł i ich ewaluację na czterech poziomach | 3 RAG |
| **3** | workflow decyzyjny i rozmowę | 4 Graphs |
| **4** | agenta z narzędziami i badanie zespołu wielu agentów | 5 Tools and Agents |
| **5** | serwer MCP i finalnego asystenta | 6 MCP |

Każdy miniprojekt jest publikowany po zamknięciu poprzedniego i korzysta z twojego kodu z wcześniejszych miniprojektów.

## Zaliczenie

Każdy miniprojekt kończy się testem z 10 pytań na platformie **Edux** (4 odpowiedzi, 1 poprawna, 48 h, 3 podejścia):
- pytania 1–5: teoria (przeczytaj `CONCEPTS.md` w folderze miniprojektu),
- pytania 6–10: te same pojęcia zastosowane do Kovalo. Pokazują wyniki, liczby albo krótki fragment kodu i pytają, co z nich wynika albo co jest nie tak.

Odpowiedzi na pytania testowe nie wymagają dostępu do wyników twojego programu: każde pytanie zawiera potrzebne dane. Da się go zaliczyć bez uruchamiania projektu, np. bez dostępu do płatnego LLM-a. Samodzielne wykonanie projektu ułatwia jednak przygotowanie do testu, ponieważ pytania dotyczą sytuacji pojawiających się podczas pracy nad systemem.

