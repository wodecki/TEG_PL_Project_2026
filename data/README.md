# data/: tylko do odczytu

| Ścieżka | Zawartość |
|---|---|
| `corpus/*.md` | 18 dokumentów Kovalo (zwykły Markdown). Przeczytaj kilka, ale ich nie zmieniaj. |
| `corpus/catalog.csv` | metadane dokumentów: jeden wiersz na plik (doc_id, file, title, doc_type, department, owner, effective_date, language) |
| `company/` | dane firmy Kovalo do Miniprojektu 4: miesięczny OTIF, faktury w groszach, warunki OTIF z umów ([README tego folderu](company/README.md)) |
| `eval/mini_project_5_conversations.yaml` | 5 rozmów Miniprojektu 5, które przechodzą przez wszystkie ścieżki asystenta, z ręcznie sprawdzonym wzorcem |
| `eval/mini_project_4_questions.yaml` | 9 pytań Miniprojektu 4 z ręcznie wyliczonym wzorcem |
| `eval/mini_project_1_queries.yaml` | 10 pytań menedżerów, na których testujemy wyszukiwanie z Miniprojektu 1; przy każdym dokument, który na nie odpowiada |
| `embeddings/cache/` | pamięć podręczna (ang. cache) wektorowych reprezentacji tekstu (ang. embeddings) obsługiwana przez LangChain (`LocalFileStore`): prawdziwe wektory OpenAI dla każdego fragmentu dokumentu (ang. chunk) zgodnego z ustawieniami kursu i każdego pytania testowego, dzięki czemu Miniprojekt 1 nie wykonuje płatnych wywołań. Twoje własne pytania (`try_search.py`, `ask.py`, programy na żywo) OpenAI zamienia na embeddingi na bieżąco, a te wektory nigdy tu nie trafiają, dzięki czemu dołączona pamięć podręczna pozostaje niezmieniona. Nie usuwaj zawartości tego katalogu. |
