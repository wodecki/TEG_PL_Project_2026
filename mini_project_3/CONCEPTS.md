# Miniprojekt 3 – pojęcia: przeczytaj przed testem

Test z Miniprojektu 3 dotyczy poniższych pojęć. Pytania 1–5 sprawdzają ich znajomość bezpośrednio. Pytania 6–10 dotyczą ich zastosowania w Kovalo. Każde zawiera potrzebne dane: wniosek, mały graf, zapis rozmowy albo fragment kodu. Do udzielenia odpowiedzi nie jest wymagane uruchamianie kodu. Wcześniejsze zbudowanie przepływu pracy (ang. workflow) ułatwi jednak zrozumienie omawianych zagadnień.

## Dlaczego Miniprojekt 3 jest ważny

> „Kiedy menedżer pyta, czy może dać rabat, chcę, żeby polityka była zastosowana dokładnie, żeby system wskazał właściwą osobę zatwierdzającą i żeby człowiek zatwierdził rabat, zanim cokolwiek obiecamy. I chcę z tym rozmawiać, a nie wypełniać formularz”. (dyrektor operacyjny)

```
Miniprojekt 1  dokumenty -> wyszukiwanie
Miniprojekt 2  wyszukiwanie -> odpowiedzi z odwołaniami do źródeł -> ewaluacja
Miniprojekt 3  odpowiedzi -> workflow decyzyjny i rozmowa                 <- jesteś tutaj
Miniprojekt 4  workflow -> agent z narzędziami
Miniprojekt 5  wszystko -> jeden standardowy interfejs (MCP) i końcowy asystent
```

## Kluczowe pojęcia

**Reguły w kodzie, nie w prompcie.** Można wkleić POL-001 do promptu i zapytać LLM-a, kto zatwierdza rabat. Może odpowiedzieć poprawnie, lecz sama odpowiedź nie pozwala wiarygodnie stwierdzić, czy model zastosował regułę bezbłędnie. Silnik reguł w zwykłym kodzie za każdym razem daje tę samą odpowiedź, da się go przetestować na każdej granicy (5% / 5,01%, 9% / 8,99%) i wypisuje, *dlaczego* tak zdecydował. Zadanie LLM-a zawęża się do tego, co robi dobrze: zrozumienia wiadomości.

**Zapisanie interpretacji.** Polityki mają luki. POL-001 nie mówi, czy przy marży poniżej minimalnej CFO *zastępuje* drugą osobę zatwierdzającą, czy do niej *dołącza*, ani co się dzieje, gdy mają zastosowanie dwa wyjątki. Kod wymusza rozstrzygnięcie. Przyjęta na potrzeby kursu konwencja `course-v1` odpowiada wprost (CFO dołącza; wybierany jest najniższy uprawniony poziom), ma numer wersji i jest zwracana z każdą decyzją. „Wybierany jest najniższy” to wybór *liberalny*; inna firma mogłaby wybrać bardziej rygorystyczny. Chodzi o to, żeby wybór był zapisany i przetestowany, a nie ukryty w prompcie.

**Grafy stanów.** LangGraph modeluje workflow jako **węzły** (funkcje, które czytają stan i zwracają jego zmiany) połączone **krawędziami**. **Krawędź warunkowa** wybiera następny węzeł na podstawie stanu: rodzaju wiadomości albo tego, czy brakuje marży. Krawędź może prowadzić z powrotem do tego samego węzła. Taka **pętla** pozwala np. pytać ponownie, aż odpowiedź będzie prawidłowa. **Stan** to typowany słownik, który każdy węzeł czyta i aktualizuje: `messages` gromadzi rozmowę, pozostałe pola opisują bieżącą sytuację.

**Pauzy: człowiek w pętli (ang. human in the loop).** `interrupt(payload)` **zatrzymuje** graf wewnątrz węzła i przekazuje `payload` programowi, np. „potrzebna akceptacja CFO”. Program pokazuje go człowiekowi i wznawia graf poleceniem `Command(resume=answer)`. Wynikają z tego dwie rzeczy:
1. **Pauza wymaga mechanizmu zapisu stanu (ang. checkpointer).** Mechanizm ten zapisuje stan wątku, żeby przebieg dało się później wznowić. Bez niego `Command(resume=...)` się nie uda.
2. **Przy wznowieniu zatrzymany węzeł uruchamia się ponownie od początku.** Tym razem `interrupt()`, zamiast zatrzymać graf, zwraca odpowiedź. Wszystko, co w tym węźle stoi przed `interrupt()`, wykona się więc dwa razy. Nigdy nie umieszczaj tam wywołania LLM-a ani efektu ubocznego (wysłania e-maila, zapisu zamówienia). Dlatego rozumienie wiadomości ma u nas własny węzeł, który działa przed każdą pauzą.

**Pauza to nie uprawnienie.** Workflow może *zapytać* CFO, ale nie potwierdza to tożsamości ani uprawnień osoby obsługującej program. Nasze akceptacje to jawna symulacja: jedna decyzja na każdą wymaganą rolę, zapisana dla jednej wersji wniosku. Prawdziwa tożsamość, zapis w CRM-ie i obietnice wobec klientów są poza zakresem tego miniprojektu.

**Stan rozmowy a historia.** **Historia** (lista wiadomości) to to, co zostało powiedziane. **Stan** opisuje aktualną sytuację: bieżący wniosek z polami i wersją, jego status, akceptacje. Każda nowa wiadomość jest rozumiana w kontekście historii, a potem kod aktualizuje stan na podstawie tej interpretacji:
- **nowy** wniosek powstaje niezależnie od poprzedniego i nie dziedziczy jego danych: zamówienie wody nie może odziedziczyć „wyprzedaży końcówek” po poprzednim zamówieniu jogurtu;
- **aktualizacja** obejmuje tylko wymienione pola i tworzy nową **wersję** (ang. revision), a wcześniejsze akceptacje jej nie obejmują.

Pytanie „kto zatwierdziłby 22%?” to **pytanie o politykę**: informacja, bez pauzy, nic nie zostaje złożone. Workflow akceptacji uruchamia dopiero wyraźna prośba o przesłanie wniosku. Liczba w wiadomości to jeszcze nie wniosek.

**Pytania uzupełniające.** Pytanie „A 22%?” bez kontekstu rozmowy jest niejednoznaczne. Krok rozumienia wiadomości przepisuje je na pytanie **samodzielne** (ang. standalone), zrozumiałe bez reszty rozmowy („Kto zatwierdza rabat 22% dla zwykłego klienta?”). Z takiego pytania może korzystać reszta workflow, w tym wyszukiwanie z Miniprojektu 2.

**Ewaluacja workflow etap po etapie.** Zła odpowiedź końcowa może pochodzić z każdego etapu: źle odczytanej wiadomości, źle zaktualizowanego wniosku, źle zastosowanej polityki, pauzy w złym miejscu. Oceniaj każdy etap osobno: kierowanie, odczytane pola, stan wniosku, osoby zatwierdzające, pauzy, status końcowy. Do tego dwie zasady:
1. **Niezależny wzorzec oczekiwanego wyniku (ang. test oracle):** oczekiwane osoby zatwierdzające we wzorcu zostały wyliczone *ręcznie*. Gdyby wyliczył je ten sam silnik reguł, który testujemy, ten sam błąd mógłby wystąpić zarówno w odpowiedzi, jak i we wzorcu używanym do jej oceny.
2. **Ustalone zrozumienie wiadomości:** `check.py` odtwarza dialogi z *idealnym* zrozumieniem (bez LLM-a), więc testuje sam workflow na tych scenariuszach. `run_dialogues.py` używa twojego LLM-a. Porównanie obu wyników jest przydatne, ale nie mierzy dokładnie błędów LLM-a: przebieg na żywo także oblicza embeddingi pytań i generuje odpowiedzi na bieżąco, a jego stan może się rozminąć ze scenariuszem. Przyczyny szukaj w konkretnych turach i pauzach.

**Cykl życia wymaga testów przejść.** Workflow, który przechodzi każdą zaplanowaną rozmowę, nadal może się mylić *między* nimi. Nasza pierwsza wersja się myliła. Po odrzuceniu ponowne złożenie tego samego wniosku kończyło się statusem **approved**, bo kod sprawdzał, czy każda rola *odpowiedziała*, a nie, czy *zatwierdziła*. Z kolei po anulowanym wniosku prawidłowe doprecyzowanie następnego wniosku kończyło się statusem **cancelled**, bo stary status nigdy nie był zerowany. Oba przypadki mają teraz testy: odrzucenie → ponowne złożenie, anulowanie → nowy wniosek, anulowanie przy doprecyzowaniu, ponowne złożenie zatwierdzonego wniosku. Naprawiła to zasada: cykl życia wniosku zaczyna się w jednym miejscu (świeży status; akceptacje zostają tylko dla niezmienionego, w pełni zatwierdzonego wniosku), a „zatwierdzony” oznacza, że **wartość każdej wymaganej roli to „approved”**.

**Błąd zaobserwowany w ewaluacji.** Pierwsza, krótsza wersja promptu rozumienia wiadomości (jeszcze w angielskiej edycji kursu) traktowała podziękowanie „Thanks!” jak pytanie i przepisywała je na *poprzednie* pytanie, więc copilot odpowiedziałby na nie jeszcze raz. Jawna definicja `other` w prompcie naprawiła to w trzech przebiegach na żywo w tamtej edycji, a w naszym przebiegu polskiej edycji „Dzięki!” również trafia do `other`. Wynik dotyczy tego niewielkiego zestawu przykładów i nie gwarantuje poprawności we wszystkich sytuacjach.

## Na co zwrócić uwagę w wynikach

Nie masz własnych wyników? Skorzystaj z przebiegu referencyjnego w [README](README.md).

1. **Odtworzenie a przebieg na żywo.** Czy `run_dialogues.py` wypada na którymś etapie gorzej niż odtworzenie w `check.py`? W których turach i co LLM odczytał źle?
2. **D4.** Drugie zamówienie (woda dla Żabki nr 12) jest nowe: czy flaga wyprzedaży końcówek się wyzerowała? Kto musiałby zatwierdzić rabat, gdyby się nie wyzerowała?
3. **D2.** Dlaczego po „Jednak zróbmy 22%” potrzebna była nowa akceptacja i czyja?
4. **D3.** Gdzie workflow się zatrzymał i w jakiej kolejności?
5. **Polityka a wniosek.** Porównaj D1 („A 22%?”, czyli „Kto zatwierdza rabat 22% dla zwykłego klienta?”) ze zmianą na 22% w D2: ten sam silnik reguł, inny przebieg workflow. Dlaczego?
