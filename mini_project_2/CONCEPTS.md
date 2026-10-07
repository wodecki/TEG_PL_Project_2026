# Miniprojekt 2 – pojęcia: przeczytaj przed testem

Test z Miniprojektu 2 dotyczy poniższych pojęć. Pytania 1–5 sprawdzają ich znajomość bezpośrednio. Pytania 6–10 dotyczą ich zastosowania w Kovalo: każde podaje własne dane (tabelę, odpowiedź, fragment kodu). Do udzielenia odpowiedzi nie jest wymagane uruchamianie kodu. Wcześniejsze wykonanie projektu ułatwi jednak zrozumienie omawianych zagadnień.

## Dlaczego Miniprojekt 2 jest ważny

> „Chcę dostać odpowiedź razem ze źródłami. I chcę wiedzieć, jak często odpowiedzi są poprawne, zanim zacznie na nich polegać czterdziestu menedżerów”. (dyrektor operacyjny)

```
Miniprojekt 1  dokumenty -> tokeny -> chunki -> embeddingi -> wyszukiwanie
Miniprojekt 2  wyszukiwanie -> odpowiedzi z odwołaniami do źródeł -> ewaluacja   <- jesteś tutaj
Miniprojekt 3  odpowiedzi -> workflow decyzyjny i rozmowa
Miniprojekt 4  workflow -> agent z narzędziami
Miniprojekt 5  wszystko -> jeden standardowy interfejs (MCP) i końcowy asystent
```

## Kluczowe pojęcia

**Kontekst we fragmentach dokumentów (ang. chunks).** Wyszukiwarka i duży model językowy (ang. large language model, LLM) przetwarzają wybrane fragmenty, bez dostępu do pozostałej części dokumentu. Jeśli fragment nie zawiera informacji o swoim pochodzeniu, nie można jej uwzględnić podczas wyszukiwania ani generowania odpowiedzi. W Miniprojekcie 1 chunk z klauzulą o karze w umowie SUP-114 nie zawiera kodu „SUP-114” ani tytułu umowy. Krok 1 dzieli każdy dokument według jego własnych nagłówków sekcji i zaczyna każdy chunk od „<tytuł> > <sekcja>”.

Co to dało na naszych 10 pytaniach z odpowiedzią w korpusie:
- **wyszukiwanie bez zmian:** hit@1 i hit@3 9/10 przy obu podziałach;
- **mniej pytań z kompletem informacji źródłowych:** komplet fraz dowodowych 8/10 zamiast 9/10. Przy M10 („Co dostarcza nam dostawca SUP-207?”) wyszukiwanie znalazło właściwy dokument, ale nie sekcję, która wymienia dostarczane wody;
- **nadal nieudane wyszukiwanie po identyfikatorze:** M03 („Co SUP-114 mówi o karach?”) nie znajduje umowy CON-101 przy żadnym podziale. W wariancie z kontekstem „SUP-114” występuje w nagłówku każdego chunku tej umowy, a mimo to pierwsze trzy miejsca zajmuje umowa SUP-207;
- **krótsze prompty:** średnio 610 zamiast 850 tokenów, czyli o około 28% mniej, bo chunki są mniejsze.

Na dziesięciu pytaniach z Miniprojektu 1 obraz jest podobny: nic się nie poprawiło, żaden z dwóch sposobów podziału nie prowadzi do trafnego wyniku dla Q10 (SUP-114), a przy Q03 o dostawcę nabiału trafny dokument spadł z pierwszego miejsca na trzecie, bo pierwsza jest teraz notatka z posiedzenia zarządu. Wynik dotyczy tego korpusu i nie stanowi ogólnej prawidłowości. To także zmiana *łączona* (podział na sekcje **i** prefiks z tytułem), więc dane nie powiedzą, która część za co odpowiada. Chunki z kontekstem zostają w projekcie, bo skracają prompty, każdy fragment zawiera informację o swoim pochodzeniu, a kolejne miniprojekty korzystają z tego indeksu. Nie poprawiają jednak wyszukiwania na polskim korpusie.

**Dokładne identyfikatory.** Reprezentacja wektorowa tekstu (ang. embedding) oddaje ogólne znaczenie, a nie dokładne znaki. W naszym pomiarze model embeddingów nie odróżnił „SUP-114” od „SUP-207”: pytanie o kary w umowie SUP-114 bardziej pasowało do umowy SUP-207, która też mówi o karach (że ich nie ma). **Wyszukiwanie leksykalne** (np. BM25) dopasowuje dokładne tokeny, więc odróżnia jeden kod od drugiego. **Wyszukiwanie hybrydowe** łączy oba rankingi. To naturalny następny krok przy pytaniach o kody, numery i nazwy, ale jego skuteczność, podobnie jak każdą zmianę sposobu wyszukiwania, trzeba sprawdzić na własnym zestawie pytań: na naszym polskim korpusie tego nie zrobiliśmy.

**Ponowne porządkowanie wyników (ang. reranking).** Innym podejściem jest pobranie 10–20 fragmentów, a następnie uporządkowanie ich przez dodatkowy model. Model oceniający wspólnie pytanie i fragment (ang. **cross-encoder**) analizuje oba teksty *razem*, co bywa dokładniejsze niż porównanie dwóch osobnych embeddingów, ale jest wolniejsze. Opcje różnią się kosztem wdrożenia:

| metoda | co kosztuje | wynik na naszym polskim korpusie (hit@1, hit@3 z 10) |
|---|---|---|
| wyszukiwanie wektorowe (Miniprojekt 1) | – | 9, 9 |
| FlashRank (dwa małe modele angielskie) | model 4–22 MB | nie mierzyliśmy |
| bge-reranker-base (angielski) | PyTorch, około 1 GB | nie mierzyliśmy |
| bge-reranker-v2-m3 (wielojęzyczny) | PyTorch i model około 2 GB; wolniejszy | nie mierzyliśmy |
| LLM porządkuje kandydatów | kilka tysięcy tokenów na pytanie; niedeterministyczny | nie mierzyliśmy |
| chunki z tytułem i sekcją (krok 1) | jednorazowe embeddingi, dołączone do kursu | 9, 9; prompt o około 28% krótszy |

W angielskiej wersji projektu rerankery wytrenowane tylko na angielskim *pogorszyły* wyniki: gorzej radziły sobie z pytaniami między językami. Nasz korpus jest teraz w większości po polsku, więc wybór takiego modelu byłby ryzykowny, ale tego nie zmierzyliśmy. Przydatność techniki zależy od danych i zadania. Przed jej wyborem porównaj wyniki na własnym zestawie pytań.

**Odpowiedź w ustalonym schemacie (ang. structured output).** Zamiast prosić o tekst w dowolnej formie i samodzielnie analizować jego strukturę, podajesz modelowi schemat (klasę Pydantic), który model musi wypełnić: `answer`, `citations`, `answerable`. Program może wówczas odczytywać określone pola odpowiedzi. Nie gwarantuje to jednak sukcesu każdego wywołania: mniejsze modele czasem zwracają coś, co do schematu nie pasuje. Solidny program zapisuje to jako **błąd**, zamiast przerywać działanie lub zgadywać brakujące wartości.

**Odwołania do źródeł.** Odwołanie wskazuje źródło, na które powołuje się model. To trzy osobne pytania: czy odwołanie **jest**, czy jest **prawidłowe** (dokument naprawdę był w kontekście) i czy jest **trafne** (to dokument, który zawiera odpowiedź). Żadne z nich nie mówi, czy odpowiedź jest *poprawna*: model może powołać się na właściwą politykę i mimo to wskazać złą osobę zatwierdzającą.

**Cztery poziomy ewaluacji.**

1. **Wyszukiwanie (ang. retrieval):** czy znaleziono trafny dokument (hit@k)?
2. **Dowody:** czy znaleziony *tekst* zawiera fakty potrzebne do udzielenia odpowiedzi? W kroku 3 sprawdzamy obecność **fraz dowodowych**, czyli sformułowań wskazujących związki między faktami (wiersz tabeli, np. `powyżej 25 000 PLN | CFO`, albo zdanie), bo luźne słowa, takie jak „CFO”, występują w wielu dokumentach. To nadal przybliżenie. Pierwsza wersja wzorca dla M02 wymagała dokładnego wyniku OTIF za lipiec, „94,6%”, i uznawała dowody za niepełne, choć znaleziony tekst mówił wprost, że za lipiec należy się kara za „dwa pełne punkty, 4%”. Model miał rację, a nasze sprawdzenie się myliło. **Ewaluatora też trzeba sprawdzić.**
3. **Odpowiedź:** czy odpowiedź podaje wymagane fakty? Czy jest poprawna?
4. **Odwołania do źródeł:** są, są prawidłowe, są trafne.

Dla każdego poziomu określamy osobno zbiór ocenianych pytań, czyli mianownik wyniku: hit@k liczy tylko pytania, na które korpus *może* odpowiedzieć, a prawidłowość odwołań tylko pytania z udzieloną odpowiedzią. Sprawdzenia odwołań są niezależne: odpowiedź może wskazać trafny dokument **i** zarazem nieprawidłowy (taki, którego nie było w jej kontekście); raport pokaże oba. Błędy liczy się na **wszystkich** pytaniach, więc żadne nieudane wywołanie nie wypada z rachunku. Jedna liczba „trafności” ukrywa, który poziom zawiódł.

**Odmowa a błąd.** *Odmowa* to odpowiedź modelu: „dokumenty tego nie zawierają” (`answerable=false`). Jest **trafna**, gdy korpus nie odpowiada na pytanie. Gdy korpus *może* odpowiedzieć, spójrz na frazy dowodowe: jeśli ich brakuje, problem jest raczej w wyszukiwaniu; jeśli są, odmowa jest raczej niesłuszna. Oba przypadki to sygnały do sprawdzenia, a nie werdykty, bo frazy są tylko przybliżeniem. W naszym przebiegu referencyjnym model odmówił przy M03 i M10, oba razy bez fraz dowodowych w tekście: wyniki wskazują więc na brak potrzebnych informacji w wyszukanym kontekście. *Błąd* to brak jakiejkolwiek czytelnej odpowiedzi i nigdy nie liczy się jako trafna odmowa: w przeciwnym razie awaria modelu mogłaby zostać uznana za uzasadnioną ostrożność.

**Pokrycie kluczowych faktów.** Sprawdzenie, czy odpowiedź zawiera wymagane frazy („CFO”, „4%”), jest darmowe, szybkie i przejrzyste. Ale to **pokrycie, a nie poprawność**: „nie CFO” też zawiera „CFO”. Dopasowanie całych fraz nie znajdzie „9%” wewnątrz „19%”, ale nie rozumie znaczenia. Nie rozpoznaje też odmiany: „dyrektor handlowy” i „dyrektora handlowego” to dla niego różne frazy, więc wzorzec wymienia odmienione formy jako osobne warianty.

**Model oceniający, czyli sędzia (ang. LLM-as-judge).** Drugie wywołanie LLM-a ocenia odpowiedź według ustalonych kryteriów (rubryki oceny): czy jest poprawna? Czy jest oparta na kontekście? Sędzia może uwzględniać znaczenie, w tym przeczenia i parafrazy, których nie rozpoznaje proste dopasowanie tekstu. Kosztuje, może się mylić, a ten sam model oceniający własne odpowiedzi może mieć te same słabe punkty. Przekaż sędziemu **zapisany** kontekst, który widział model odpowiadający, a nie nowe wyszukiwanie.

**Narzędzia i biblioteki do ewaluacji (ang. evaluation frameworks)** oferują gotowe metryki oparte na sędziach. Nasze opcjonalne porównanie używa **DeepEval**; innym znanym frameworkiem jest **RAGAS**. Bez względu na bibliotekę wiedz, co mierzy każda metryka:

- **Wierność źródłom (ang. faithfulness):** udział twierdzeń odpowiedzi popartych znalezionym kontekstem. Mierzy oparcie w źródłach: odpowiedź wierna źródłom może mimo to pominąć fakty, których wymagało pytanie. Sprawdź domyślne ustawienia biblioteki: DeepEval przepuszcza też twierdzenia, których kontekst ani nie potwierdza, ani nie podważa, chyba że ustawisz `penalize_ambiguous_claims=True` (nasze ustawienie).
- **Poprawność na poziomie twierdzeń** (np. FactualCorrectness w RAGAS, `mode=f1`): porównuje twierdzenia odpowiedzi z twierdzeniami odpowiedzi wzorcowej i podaje ich **F1**. Jeśli odpowiedź zawiera 1 twierdzenie, wzorzec 2, a to jedno jest poprawne, to precyzja (ang. precision) = 1/1, pełność (ang. recall) = 1/2, a F1 = 2·(1·0,5)/(1+0,5) ≈ 0,67. To definicja w działaniu, a nie błąd: odpowiedź pominęła twierdzenie ze wzorca. Może to być twierdzenie, którego pytanie wcale nie wymagało.
- **G-Eval** (DeepEval): LLM ocenia w skali od 0 do 1 kryterium, które opisujesz zwykłymi słowami. Najpierw sam układa kroki oceny, a na końcu podaje uzasadnienie.

Gdy twój sędzia i framework się nie zgadzają, przyczyny mogą być trzy:
1. **definicja metryki albo to, jak sędzia ją zastosował:** F1 wobec dłuższego wzorca, jak wyżej. Albo G-Eval w naszym przebiegu: jego wygenerowane kroki dopuszczają dodatkowe poprawne szczegóły, a mimo to uzasadnienia dla dwóch poprawnych odpowiedzi (M01, M07) wymieniają te szczegóły obok niższej oceny. To sugeruje karę, której kroki nie przewidują;
2. **powtarzalna anomalia oceny:** w angielskiej wersji projektu RAGAS 0.4.3 (nasze porównanie sprzed przejścia na LangChain 1) dawał zdaniu „A stock write-off above 25,000 PLN is approved by the CFO.” F1 = 0,00 wobec wzorca „A write-off above 25,000 PLN is approved by the CFO.” we wszystkich sześciu przebiegach. Nie ustaliliśmy przyczyny;
3. **zmienność między przebiegami:** w tej samej angielskiej wersji ta sama odpowiedź na M08 dostawała od RAGAS faithfulness 1,00 w jednych przebiegach i 0,75 w innych.

Żaden z ewaluatorów nie jest prawdą ostateczną, a uzasadnienie sędziego też jest twierdzeniem. W naszym przebiegu DeepEval uzasadnił niską ocenę M09 m.in. tym, że w źródle nie ma frazy „głównie w firmie Hurtix”, a fraza ta występuje tam dosłownie. **Porównaj uzasadnienie z ocenianą odpowiedzią, źródłem i kryteriami oceny.**

**Ograniczenia zakresu oceny.** Ewaluacja mierzy tylko to, do czego ją zaprojektowano. W naszym przebiegu referencyjnym odmowa przy M11 („Ile zarabia nasz CEO?”) kończy się słowami „na podstawie उपलब्धnych materiałów”: model wstawił w polskie słowo „dostępnych” fragment pisma dewanagari. Odmowa była trafna i tak też ją policzono: żaden z czterech poziomów nie czyta tekstu odmowy. Podobnie przy M09 drugie zdanie odpowiedzi przekręca notatkę („Hurtix oferuje sklepy convenience … napojami”), a pokrycie faktów, nasz sędzia i DeepEval tego nie zauważyli. Prompt każe odpowiadać w języku pytania, także gdy dokument jest w innym języku; przy M04 (angielski dokument PL-601) odpowiedź była po polsku. To dowód z jednego przebiegu, a nie gwarancja.

## Na co zwrócić uwagę w wynikach

Nie masz własnych wyników? Skorzystaj z przebiegu referencyjnego w [README](README.md).

1. **Najpierw pojedyncze pytania, potem sumy.** Które pytanie w `run_retrieval_eval.py` zmieniło się między chunkami z Miniprojektu 1 a chunkami z kontekstem? Spójrz na identyfikatory znalezionych chunków: dlaczego? Co zwróciło wyszukiwanie przy M03 i czym te chunki różnią się od szukanej umowy?
2. **Dowody a odpowiedź.** Czy w twoim przebiegu jest pytanie z niepełnymi dowodami i mimo to poprawną odpowiedzią? Skąd model wziął fakt? W naszym przebiegu oba pytania z niepełnymi dowodami (M03, M10) skończyły się odmową.
3. **Odmowy.** Jak twój LLM poradził sobie z dwoma pytaniami spoza korpusu? Czy odmówił i czy słusznie? Czy odmówił też przy pytaniu, na które korpus odpowiada, i co wtedy mówiły frazy dowodowe?
4. **Błędy.** Ile błędów miał twój przebieg? Przy innym LLM-ie porównaj z przebiegiem referencyjnym.
5. **Trzech ewaluatorów** (opcjonalnie, z DeepEval; wystarczy też zapisane porównanie z README). Wybierz pytanie, przy którym pokrycie kluczowych faktów, twój sędzia i DeepEval różnią się najbardziej. Porównaj uzasadnienie DeepEval z odpowiedzią, znalezionym fragmentem i kryteriami oceny: kto ma rację? Która z trzech przyczyn opisanych wyżej to wyjaśnia?
