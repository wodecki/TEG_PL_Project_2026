# Miniprojekt 1 – pojęcia: przeczytaj przed testem

Test z Miniprojektu 1 dotyczy poniższych pojęć. Pytania 1–5 sprawdzają ich znajomość bezpośrednio. Pytania 6–10 dotyczą ich zastosowania w Kovalo: pokazują wyniki wyszukiwania, liczby tokenów albo fragment kodu i pytają, co z nich wynika. Każde pytanie zawiera wszystkie potrzebne dane, więc do udzielenia odpowiedzi nie jest wymagane uruchamianie kodu. Wcześniejsze wykonanie projektu ułatwi jednak zrozumienie omawianych zagadnień.

## Dlaczego Miniprojekt 1 jest ważny

> „Zanim zaczniemy rozmawiać o odpowiedziach AI, pokażcie mi dwie rzeczy. Po pierwsze, że system znajduje właściwy dokument, kiedy pytam własnymi słowami. Po drugie, ile będzie kosztował miesięcznie, jeśli czterdziestu menedżerów będzie z niego korzystać codziennie”. (dyrektor operacyjny)

W Miniprojekcie 2 duży model językowy (ang. large language model, LLM) odpowiada na pytania na podstawie wyszukanych fragmentów dokumentów (ang. chunks). Rzetelność odpowiedzi zależy od tego, czy otrzyma odpowiednie materiały źródłowe. Dlatego zaczynamy od wyszukiwania właściwych fragmentów (ang. retrieval).

```
Miniprojekt 1  dokumenty -> tokeny -> chunki -> embeddingi -> wyszukiwanie   <- jesteś tutaj
               + twój LLM, podłączony i zmierzony
Miniprojekt 2  wyszukiwanie -> odpowiedzi z odwołaniami do źródeł
Miniprojekt 3  odpowiedzi -> workflow decyzyjny
Miniprojekt 4  workflow -> agent z narzędziami
Miniprojekt 5  agent -> integracja przez MCP
```

## Kluczowe pojęcia

**Tokeny.** Modele przetwarzają tekst w jednostkach zwanych tokenami, a dostawcy na ich podstawie naliczają opłaty. Token nie musi odpowiadać całemu słowu. Narzędzie dzielące tekst na tokeny (ang. tokenizer), korzystające z algorytmu BPE, łączy często występujące ciągi znaków w pojedyncze tokeny. Popularne angielskie słowa to często jeden token, a rzadkie słowa, liczby i wiele słów w innych językach, w tym w polskim, dzielą się na kilka tokenów. Zmierzyliśmy to na tym samym tekście w obu językach: 18 dokumentów Kovalo zajmuje po polsku około 1,6 raza więcej tokenów niż po angielsku (8943 wobec 5520 w `o200k_base`). Przy tej samej cenie za token przetworzenie polskiej wersji tych dokumentów kosztuje więc więcej. Liczba tokenów zależy też od tokenizera: ten sam tekst ma inną liczbę tokenów w `cl100k_base` i w `o200k_base`.

**Koszt.** Koszt wywołania obliczamy jako sumę: liczba tokenów wejściowych × cena za token wejściowy + liczba tokenów wyjściowych × cena za token wyjściowy. Projekt przyjmuje ceny z cennika OpenAI z października 2026 r., więc każdy dostaje te same liczby; prawdziwe cenniki się zmieniają. Tokeny wyjściowe są zwykle kilka razy droższe od wejściowych.

**Trzy sposoby dostępu do LLM-a.** Model możesz wywołać bezpośrednio u jego twórcy (OpenAI), przez **integratora** (OpenRouter: jedno API i jeden klucz do modeli wielu dostawców, więc łatwo zmienić model) albo samodzielnie utrzymywać i uruchamiać model (ang. **self-hosting**), np. model o otwartych wagach za pomocą Ollamy. Przy self-hostingu nie płacisz za tokeny, a dane nie opuszczają twojego komputera. Trzeba jednak zapewnić odpowiedni sprzęt, a niewielkie modele działające na laptopie mogą ustępować modelom dostępnym przez API pod względem szybkości i jakości odpowiedzi. Przy korzystaniu z integratora treść przekazywana modelowi, czyli prompt, trafia zarówno do integratora, jak i do dostawcy modelu. LangChain ukrywa te różnice: `init_chat_model` buduje każdy z tych modeli, a reszta kodu się nie zmienia.

**Kto liczy tokeny.** Twoje oszacowanie liczy tokeny tokenizerem `o200k_base`, którego używają obecne modele OpenAI. Dostawca liczy je tokenizerem swojego modelu i dolicza kilka tokenów, które opakowują prompt w wiadomość czatu. Dlatego przy modelach OpenAI rzeczywista liczba jest bliska twojemu oszacowaniu, a przy innych rodzinach modeli odbiega od niego bardziej. Podstawą rozliczenia jest liczba tokenów podana przez dostawcę.

**Reprezentacje wektorowe tekstu (ang. embeddings).** Model embeddingów zamienia tekst na wektor liczbowy. Wektory tekstów o podobnym znaczeniu powinny znajdować się blisko siebie w tej przestrzeni. Bliskość mierzy się **podobieństwem kosinusowym**: kosinusem kąta między dwoma wektorami. Embeddingi OpenAI mają długość 1, więc ich iloczyn skalarny jest równy podobieństwu kosinusowemu.

Embeddingi oddają ogólne znaczenie, dlatego słabo radzą sobie z dokładnymi identyfikatorami: kod taki jak `SUP-114` czy nazwa produktu niesie niewiele znaczenia. **Wyszukiwanie po słowach kluczowych** (leksykalne, np. BM25) dopasowuje dokładne tokeny, a **wyszukiwanie hybrydowe** łączy oba rankingi. Skuteczność takiej zmiany trzeba sprawdzić na własnym zestawie pytań; poprawa wyników nie jest gwarantowana.

**Podział na fragmenty (ang. chunking).** Małe chunki są precyzyjne, ale mogą gubić kontekst. Duże zachowują kontekst, ale łączą w jednym wektorze niezwiązane treści. Nakładka (ang. overlap) to część tekstu powtarzana w sąsiednich chunkach. Dzięki niej granica chunku rzadziej oddziela fakt od jego kontekstu. Nie wyklucza tego jednak: fakt może być dłuższy niż nakładka, a gdy narzędzie dzielące tekst (ang. splitter) wyznacza granice między akapitami, sąsiednie chunki mogą nie mieć wspólnego tekstu. `split_documents` kopiuje metadane dokumentu do każdego chunku, dzięki czemu można ustalić dokument źródłowy każdego fragmentu.

**Pamięć podręczna (ang. cache).** Gdy ponownie liczysz embedding tego samego tekstu, płacisz drugi raz i dostajesz (prawie) ten sam wektor. `CacheBackedEmbeddings` z LangChain zapisuje każdy wektor pod kluczem złożonym z nazwy modelu i skrótu (hasha) tekstu. Dzięki temu cały proces przetwarzania (ang. pipeline) jest tańszy, szybszy i powtarzalny.

**Baza wektorowa (ang. vector store).** `InMemoryVectorStore` przechowuje każdy chunk razem z jego wektorem. Dla pytania liczy embedding pytania i zwraca chunki o największym podobieństwie kosinusowym. Liczy je funkcją `cosine_similarity`, którą piszesz w kroku 5.

**Hit@k.** Czy wśród pierwszych k wyników znalazł się trafny dokument? To najprostsza miara jakości wyszukiwania; Miniprojekt 2 się na niej opiera.

## Na co zwrócić uwagę w wynikach

Nie masz własnych wyników? Skorzystaj z przebiegu referencyjnego na końcu sekcji „Sześć kroków” w [README](README.md).

1. **Tokeny to nie słowa.** Który dokument ma najwięcej tokenów? Czy to ten sam, który ma najwięcej słów? Porównaj liczbę tokenów na słowo w dokumentach polskich i w jedynym angielskim, PL-601. To porównanie różnych tekstów; ten sam tekst w obu językach porównuje README.
2. **Znaczenie, nie słowa kluczowe.** W Q02 towar „przyjechał rozbity”, a polityka mówi o „towarze uszkodzonym”, który trzeba „zgłosić” w określonym czasie „od dostawy”. W Q06 „w ciężarówce przestanie działać lodówka”, a procedura opisuje sytuację, gdy „w trasie zepsuje się agregat chłodniczy”. Czy wyszukiwanie mimo to znalazło właściwe dokumenty?
3. **Między językami.** Q07 pyta po polsku o sprzęt ochronny dla gości w magazynie w Gdańsku, a regulamin tego magazynu (PL-601) jest po angielsku. Na którym miejscu znalazł się PL-601?
4. **Ograniczenia embeddingów.** Q10 pyta o umowę wyłącznie po kodzie dostawcy, `SUP-114`. Czy wśród trzech pierwszych chunków jest jakikolwiek chunk umowy CON-101? Porównaj wyniki podobieństwa tego pytania w `report.json` z wynikami pozostałych pytań. Dlaczego dokładny kod jest trudny dla modelu embeddingów i co mogłoby tu pomóc? To samo pytanie wraca w Miniprojekcie 2.
5. **Dlaczego nie wysłać wszystkiego?** Porównaj miesięczny koszt promptu z wynikami wyszukiwania z kosztem wysyłania za każdym razem całego korpusu (w przebiegu referencyjnym 17,78 USD wobec 69,86 USD, czyli 3,9 raza więcej). Która część rachunku jest w obu przypadkach taka sama? Co by się zmieniło przy 1800 dokumentach zamiast 18?
6. **Oszacowanie a rzeczywistość.** O ile w twoim pierwszym wywołaniu LLM-a oszacowanie tokenów wejściowych różniło się od liczby podanej przez dostawcę i dlaczego? Ile tokenów wyjściowych zużyła odpowiedź wobec 350 zakładanych w scenariuszu kosztów? Czy model podał identyfikator dokumentu, o co prosi prompt systemowy? Czy odpowiedź jest w ogóle poprawna? Sprawdź ją w dokumencie.
