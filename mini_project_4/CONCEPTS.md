# Miniprojekt 4 – pojęcia: przeczytaj przed testem

Test z Miniprojektu 4 dotyczy poniższych pojęć. Pytania 1–5 sprawdzają ich znajomość bezpośrednio. Pytania 6–10 dotyczą ich zastosowania w Kovalo. Każde zawiera potrzebne dane: warunki umowy, liczby, zapis przebiegu albo fragment kodu. Do udzielenia odpowiedzi nie jest wymagane uruchamianie kodu. Wcześniejsze zbudowanie agenta ułatwi jednak zrozumienie omawianych zagadnień.

## Dlaczego Miniprojekt 4 jest ważny

> „Niektóre pytania wymagają sięgnięcia do umowy i bieżących danych oraz obliczeń: ile winien nam dostawca, czy możemy rozwiązać umowę, kto musi coś zatwierdzić. Chcę dostać odpowiedź razem z obliczeniami, a każdą liczbę móc sprawdzić u źródła”. (dyrektor operacyjny)

```
Miniprojekt 1  dokumenty -> wyszukiwanie
Miniprojekt 2  wyszukiwanie -> odpowiedzi z odwołaniami do źródeł -> ewaluacja
Miniprojekt 3  odpowiedzi -> workflow decyzyjny i rozmowa
Miniprojekt 4  workflow -> agent z narzędziami                              <- jesteś tutaj
Miniprojekt 5  wszystko -> jeden standardowy interfejs (MCP) i końcowy asystent
```

## Kluczowe pojęcia

**Narzędzie to jego interfejs.** Kiedy model decyduje, co wywołać, widzi tylko trzy rzeczy: **nazwę** narzędzia, jego **opis** (docstring) i **schemat argumentów** (nazwy, typy, wartości domyślne). W tym projekcie model nie otrzymuje kodu implementacji narzędzia. Ogólnikowy opis („pobiera dane”) albo niewyjaśniony format („miesiąc”) może prowadzić do błędnych wywołań, nawet jeśli sama implementacja narzędzia jest poprawna. Zależności, takie jak dane czy baza wektorowa (ang. vector store), **nie** są argumentami: dostarcza je kod (domknięcie, ang. closure), więc model nie może ich wybrać ani podrobić.

**Pętla agenta.** Agent to pętla:
1. model czyta rozmowę i albo odpowiada, albo prosi o wywołania narzędzi;
2. program wykonuje wywołania i dopisuje ich wyniki do rozmowy;
3. powrót do punktu 1.

Model wybiera narzędzia, argumenty, kolejność i moment, w którym kończy. Dzięki temu jest elastyczny, ale też zawodny, więc pętla potrzebuje **limitu**: limitu kroków i limitu czasu na całe pytanie. Przed każdą nową turą modelu i każdym wywołaniem narzędzia program sprawdza limit. Gdy limit się wyczerpie, nic nowego się nie zaczyna, każdy dostarczony już wynik zostaje, a przebieg kończy się statusem `limit`. Odpowiedź końcowa, która przyjdzie po przekroczeniu limitu, zostaje zachowana, ale oznaczona jako `limit`. Limit sprawdzamy tylko między krokami: wywołanie, które już trwa, kończy się normalnie, a wywołanie, które się zawiesi, ogranicza tylko limit czasu ustawiony przez dostawcę (ang. timeout).

**Deterministyczne narzędzia, zawodne wybory.** Obliczenia wykonuje przetestowany kod, który korzysta z liczb dziesiętnych i kwot w całych groszach. Zaokrąglenie połówki w górę następuje tylko raz, na końcu. Testy obejmują wartości graniczne: niedobór 0,99 punktu procentowego oznacza 0 pełnych punktów, a niedobór 1,0 punktu oznacza 1 pełny punkt. Model ma tylko wybrać właściwe dane wejściowe. Kalkulator to **arytmetyka na danych, które dostał**: nie wie, czy kara się *należy*. To zależy od umowy, więc agent musi najpierw sprawdzić `penalty_clause`.

**Wyniki jednoznacznie opisujące stan danych.** Jeśli narzędzie zwróci dane za trzy miesiące zamiast żądanych czterech i nie zgłosi braku, agent może wyciągnąć błędny wniosek. Dlatego każdy wynik ma status, a brak danych jest jawny:
- `ok` z `missing_months: ['2026-10']`: niepełny okres, zgłoszony jako niepełny;
- `no_data`, `unknown_supplier`, `not_applicable`, `invalid_request`: zwykłe odpowiedzi, na które agent może zareagować;
- uszkodzony plik danych: **błąd**, nigdy „brak danych”.

Brak zapisu w umowie to też wartość. Umowa z Aqua Kryształ *nie ma* klauzuli kary: `penalty_clause: false`, a stawka zostaje pusta (nie 0, bo 0 oznaczałoby klauzulę z zerową stawką).

**Możliwość a twierdzenie.** To dwie różne gwarancje:
- *możliwość* (ang. capability): agent nie ma narzędzia, które zatwierdza, zapisuje albo obiecuje. Zapewnia to sam zestaw narzędzi;
- *twierdzenie* (ang. claim): odpowiedź nigdy nie mówi „zatwierdziłem”. Można to tylko **sprawdzić** na odpowiedziach, które testujemy.

Lista dozwolonych narzędzi (ang. allowlist) blokuje działania, ale nie blokuje fałszywych zdań. Zatwierdzanie odbywa się w przepływie pracy (ang. workflow) z udziałem człowieka, zbudowanym w Miniprojekcie 3.

**Jeden agent czy zespół?** W architekturze z **agentem koordynującym (ang. supervisor)** części pytania są przekazywane **agentom specjalistycznym**. Tutaj każdy specjalista jest udostępniony jako narzędzie agenta koordynującego: to wzorzec supervisora „przez narzędzia”. Zespół może pomóc, gdy specjaliści potrzebują różnych uprawnień albo danych, albo gdy podpytania są niezależne. Wymaga jednak **przekazywania zadań między agentami** (ang. hand-offs). Przy każdym przekazaniu informacja może zostać pominięta (zlecenie ma zbyt wąski zakres) albo zmyślona (podsumowanie specjalisty mówi coś, czego nie zwróciło żadne narzędzie). Praca zespołu wymaga też większej liczby wywołań i tokenów oraz więcej czasu. Przed wyborem architektury porównaj jej wyniki i koszty. W naszych zapisanych przebiegach zlecenie supervisora dla analityka danych w T1 nie przekazało reguły 94% z umowy, więc analityk porównał OTIF z celem 97% i napisał, że nie ma zapisów o rozwiązaniu umowy. W D1 analityk dokumentów stwierdził, że POL-001 nie podaje progu marży, choć jego wyszukiwanie po prostu nie zwróciło sekcji o minimalnej marży.

**Odpowiedź specjalisty nie jest dowodem.** W zespole wygenerowana odpowiedź specjalisty trafia do supervisora jako wynik narzędzia. Gdyby program oceniający liczył każdy wynik narzędzia jako źródło, liczba zmyślona przez specjalistę miałaby „pokrycie”, a zespół dostałby lepszą ocenę, niż na to zasługuje. Dlatego zapis przebiegu zapamiętuje **pochodzenie** (ang. origin) każdego zdarzenia: `data`, `calculation` albo `worker_summary`. Źródłami są tylko dwa pierwsze. Własne wywołania danych i obliczeń specjalisty zostają w zapisie, zagnieżdżone pod wywołaniem supervisora, więc ten sam program oceniający działa dla obu architektur.

**Ocena zapisu przebiegu, test po teście.** Odpowiedź może być trafna z niewłaściwego powodu (właściwa kwota z warunków innego dostawcy) albo błędna, choć dobrze brzmi. Dlatego oceniamy **zapis przebiegu** (ang. trace), a każdy test nazywamy od tego, co mierzy:
1. **pokrycie narzędzi:** potrzebne wywołania się udały, dla właściwego dostawcy i miesięcy. Osobne wywołania się sumują (lipiec, potem sierpień, potem wrzesień), a inna poprawna droga też się liczy (lipcowy OTIF z danych albo z notatki ze spotkania). „Nie ma danych za październik” wymaga wywołania, które **zgłosiło** październik jako brakujący: wywołanie dla lipca nie mówi nic o październiku;
2. **poprawne argumenty:** każde obliczenie kary użyło danych wejściowych sprawdzonych ręcznie **i** te dane zostały pobrane w tym przebiegu (a nie wpisane z pamięci ani podsunięte przez użytkownika);
3. **pokrycie faktów w odpowiedzi:** kluczowe fakty występują w odpowiedzi jako całe frazy („nie” nie zostanie znalezione w „wypowiedzeniem”, a „7296” w „27296”);
4. **pokrycie liczb źródłami:** każda liczba z odpowiedzi występuje w tym, co narzędzie danych albo obliczeń **pobrało lub obliczyło** dla tego pytania, z tą samą **jednostką**. To, co wysłał model, a narzędzie tylko powtarza (zapytanie wyszukiwania, żądane miesiące, dane wejściowe kalkulatora), nie jest dowodem: inaczej liczba w zmyślonym zapytaniu „pokrywałaby” samą siebie. **Jeden znany wyjątek:** uzasadnienia sprawdzenia polityki powtarzają rabat podany przez model („rabat 7,3% mieści się w przedziale do 12%”), więc zmyślone 7,3% miałoby pokrycie. Te same uzasadnienia zawierają też prawdziwe progi polityki, a ten test nie odróżni jednych od drugich. `729600` groszy pokrywa „7296,00 PLN”, nigdy „729 600 PLN”; „2%” (stawka) i „2 punkty procentowe” (niedobór) to różne twierdzenia. Test czyta polski zapis liczb (przecinek dziesiętny, spacja w tysiącach) i pomija identyfikatory oraz daty (2026-07, 31.03.2027, „20 sierpnia”). Liczba niejednoznaczna, taka jak „7,296” (po polsku niecałe 7,3, po angielsku 7296), nie pokrywa niczego i nie ma pokrycia: program jej nie rozstrzyga, tylko ją zgłasza;
5. **twierdzenie o zatwierdzeniu:** sformułowanie odpowiedzi twierdzi, że coś zatwierdzono.

Żadne z tych sprawdzeń samo w sobie nie dowodzi, że odpowiedź jest poprawna:
- Liczba z pokryciem nadal może być niewłaściwa: OTIF i faktura Aqua Kryształ z warunkami Mlecznej Doliny dają „pokryte” 1926 PLN. Taki błąd wykrywa test 2.
- Liczba bez pokrycia jest **niezweryfikowana**, a nie fałszywa: wyliczone przez agenta 96,0 − 95,1 = 0,9 jest poprawne, ale wynik nie pochodzi z zarejestrowanego wywołania narzędzia obliczeniowego.
- Test faktów może zaliczyć odpowiedź, która mówi też coś przeciwnego. W zespole w D1 dał 100%, bo „CFO” padło w zdaniu o innym progu, choć odpowiedź pominęła zgodę CFO wymaganą przez minimalną marżę.

Każdy test ocenia wybrany aspekt jakości w sposób przybliżony. Łączna analiza wyników pomaga zlokalizować problem.

**Wzorzec jest niezależny.** Oczekiwane kary policzono ręcznie (lipiec: 94,6% to 2 pełne punkty poniżej 97%, więc 4% z 182 400,00 PLN = 7296,00 PLN). Nigdy nie liczą ich testowane narzędzia (lekcja o niezależnym wzorcu z Miniprojektu 3).

**Błąd zaobserwowany w ewaluacji.** W żadnym z naszych sześciu przebiegów pojedynczy agent nie odpowiedział poprawnie na T1: „Czy na koniec września 2026 r. Kovalo może rozwiązać umowę z Mleczną Doliną z powodu jej OTIF?”. Umowa wymaga trzech kolejnych miesięcy z OTIF **poniżej 94%**. W lipcu OTIF wyniósł 94,6%, więc odpowiedź brzmi „nie”, a rozstrzyga ją lipcowa liczba. W żadnym przebiegu agent nie pobrał lipcowego OTIF narzędziem danych (pokrycie narzędzi 67% za każdym razem). Cztery odpowiedzi zaczynały się od „Tak”, dwie od „Nie na podstawie samego OTIF…”, ale bez lipcowego 94,6%. W zapisanym przebiegu agent pobrał tylko wrzesień, odpowiedział „Tak” i dopisał, że brakuje mu dwóch wcześniejszych miesięcy, choć mógł je pobrać. To dwa błędy naraz: agent zbyt wcześnie przestał zbierać dane i wyciągnął wniosek, który z nich nie wynikał. Zespół dysponował danymi za wszystkie trzy miesiące, a mimo to również rozpoczął odpowiedź od „Tak”. Rozwiązanie to lekcja z Miniprojektu 3: zapisz regułę w kodzie, jako narzędzie, które samo pobiera potrzebne miesiące, i przetestuj ją na granicach (94,0 to nie mniej niż 94).

## Na co zwrócić uwagę w wynikach

Nie masz własnych wyników? Skorzystaj z przebiegów referencyjnych w [README](README.md) i w `reference_traces/`.

1. **P1–P3.** Prześledź ścieżkę dowodową: jakie warunki, OTIF i faktura trafiły do kalkulatora i skąd pochodzi każda liczba w odpowiedzi?
2. **A1.** Czy agent sprawdził `penalty_clause`, zanim stwierdził, że kara się nie należy? Czy mimo to wywołał kalkulator?
3. **T1.** Czy odpowiedź twojego agenta jest spójna od pierwszego do ostatniego zdania? Które miesiące pobrał? Co mówią o niej testy 1 i 3?
4. **N1 i S1.** Jak agent poradził sobie z brakiem danych i z 98% TransBałtu, które nie są OTIF?
5. **Zespół.** Dla jednego pytania porównaj wywołania pojedynczego agenta z przekazaniami zadań u supervisora. Czego zabrakło w zleceniu?
