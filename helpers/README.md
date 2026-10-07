# helpers/: wspólny kod, którego nigdy nie edytujesz

Wspólne moduły obsługują m.in. wektorowe reprezentacje tekstu (ang. embeddings), ich pamięć podręczną (ang. cache), zapisy przebiegów (ang. traces) i zapisywanie stanu rozmowy (ang. checkpointing).

| Plik | Co robi |
|---|---|
| `config.py` | wczytuje `config.yaml` |
| `embedding_cache.py` | podaje embeddingi z cache kursu bez klucza OpenAI; znajduje teksty, których w cache brakuje |
| `eval_queries.py` | wczytuje pytania testowe |
| `prompts.py` | układ promptu wysyłanego do LLM-a |
| `catalog.py` | czyta `data/corpus/catalog.csv` |
| `checks.py` | wspólny kod programów sprawdzających (`src/check.py`) wszystkich miniprojektów |
| `company.py` | Miniprojekt 4: dane firmy (wczytane i sprawdzone) oraz rekordy zwracane przez narzędzia |
| `quantities.py` | Miniprojekt 4: liczby, jednostki (PLN, grosze, %, punkty procentowe) i dopasowanie całych fraz dla programu oceniającego |
| `mcp_runtime.py` | Miniprojekt 5: łączy się z serwerem MCP (przez stdio albo w pamięci), sprawdza każdy wynik według rekordów z Miniprojektu 4, pilnuje limitów czasu |
| `assistant.py` | Miniprojekt 5: podmienia jeden węzeł grafu z Miniprojektu 3; jedyny punkt wejścia `assistant_turn`; miejsce, w którym jest przechowywany zapis przebiegu agenta |
| `assistant_eval.py` | Miniprojekt 5: ocenia każdą turę według oczekiwanej ścieżki |
| `agent_trace.py` | Miniprojekt 4: uruchamia agenta na jednym pytaniu i zapisuje każde wywołanie (jego pochodzenie, argumenty, wynik) w ramach jednego limitu |
| `llm_notice.py` | uwaga wypisywana przez programy na żywo, gdy używasz innego LLM-a niż referencyjny |
| `gold.py` | Miniprojekt 2: wczytuje pytania ze wzorcem (`data/eval/mini_project_2_questions.yaml`) |
| `records.py` | Miniprojekt 2: rekordy odpowiedzi i oceny (`Answer`, `Verdict`, `RunRecord`) oraz zapis i odczyt przebiegu |
| `workflow.py` | Miniprojekt 3: stan grafu, rozumienie wiadomości (`Turn`), wniosek i decyzja, checkpointer znający te typy, `run_turn` |
| `text_pl.py` | formatuje liczby zgodnie z polską notacją i przekształca odpowiedzi udzielane po wstrzymaniu grafu („7,5”, zatwierdź / odrzuć / anuluj) w wartości wykorzystywane przez graf |
