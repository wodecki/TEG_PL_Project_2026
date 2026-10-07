# Miniprojekt 5 – pojęcia: przeczytaj przed testem

Test z Miniprojektu 5 dotyczy poniższych pojęć. Pytania 1–5 sprawdzają ich znajomość bezpośrednio. Pytania 6–10 dotyczą ich zastosowania w Kovalo. Każde zawiera potrzebne dane: wynik, wiersz z dziennika zdarzeń, dwa rekordy albo fragment rozmowy. Do udzielenia odpowiedzi nie jest wymagane uruchamianie kodu. Wcześniejsze zbudowanie serwera i asystenta ułatwi jednak zrozumienie omawianych zagadnień.

## Dlaczego Miniprojekt 5 jest ważny

> „Każde narzędzie, które testujemy, wymaga od nas budowania tych samych wyszukiwań od nowa. Udostępnijcie narzędzia Kovalo przez jeden standardowy interfejs, z którego skorzysta nasz asystent i każde narzędzie, które wdrożymy później. A akceptacje mają nadal przechodzić przez ludzi”. (dyrektor operacyjny)

```
Miniprojekt 1  dokumenty -> wyszukiwanie
Miniprojekt 2  wyszukiwanie -> odpowiedzi z odwołaniami do źródeł -> ewaluacja
Miniprojekt 3  odpowiedzi -> workflow decyzyjny i rozmowa
Miniprojekt 4  workflow -> agent z narzędziami
Miniprojekt 5  wszystko -> jeden standardowy interfejs (MCP) i końcowy asystent      <- jesteś tutaj
```

## Kluczowe pojęcia

**MCP: jeden interfejs, trzy rodzaje możliwości.** Protokół udostępniania kontekstu i narzędzi modelom, MCP (ang. Model Context Protocol), określa standardowy sposób, w jaki aplikacja (*klient*) korzysta z możliwości oferowanych przez *serwer*. Serwer oferuje trzy rodzaje elementów podstawowych (ang. primitives), które różnią się tym, **kto decyduje o ich użyciu**:
- **narzędzia** (ang. tools): działania, które wywołuje **model** (sześć wyszukiwań i obliczeń Kovalo);
- **zasoby** (ang. resources): dane, które czyta **aplikacja**, wskazując je przez URI (`kovalo://documents/CON-103`);
- **prompty**, czyli szablony wiadomości: gotowe wzorce wybierane przez **użytkownika** (`supplier_review`).

Logikę biznesową pisze się raz, po stronie serwera, a każdy klient MCP (nasz asystent, MCP Inspector, Claude Desktop) korzysta z niej bez przepisywania.

**Standardowe wejście i wyjście (ang. standard input/output, stdio): lokalny proces dla każdego klienta.** Przy transporcie stdio klient **uruchamia serwer jako własny podproces** i rozmawia z nim przez stdin i stdout serwera, komunikatami JSON-RPC. Dzięki temu stdio jest proste i lokalne. Gdy czterdziestu menedżerów otworzy asystenta, powstanie czterdzieści procesów serwera: to jedna *implementacja*, a nie jedna wspólna *usługa*. Wspólny serwer na hostingu wymagałby transportu HTTP i uwierzytelniania, a to wykracza poza ten miniprojekt. Ponieważ stdout **jest** kanałem protokołu, serwer nie może wypisywać tam przez `print()` niczego innego: dodatkowy wiersz narusza protokół i może zakłócić działanie klienta. Komunikaty diagnostyczne należy kierować na standardowe wyjście błędów (stderr).

**Kontrakt narzędzia: schemat wejścia i wyjścia.** Narzędzie MCP publikuje `inputSchema` (swoje argumenty), a od wprowadzenia wyników w ustalonym schemacie (ang. structured output) także `outputSchema` (swój wynik). Zwraca wtedy `structuredContent`, czyli obiekt JSON, na którym program może polegać, oraz kopię tekstową do wyświetlenia. Jeśli typ zwracany narzędzia FastMCP oznaczysz klasą rekordu, SDK opublikuje oba schematy. Przy adnotacji `-> dict` w wersji SDK przypiętej w tym projekcie klient dostaje tylko tekst.

**Sprawdzaj zgodność z WŁASNYM kontraktem, zanim cokolwiek uzupełni wartości domyślne.** Klienta, który ufa schematowi serwera, może oszukać nakładka, która usuwa pole i ze schematu, i z wyniku. Nasz klient sprawdza zgodność każdego wyniku z **rekordem z Miniprojektu 4** (kanonicznym kontraktem):
- wszystkie pola są obecne i nie ma żadnych dodatkowych;
- typy są ścisłe: żadnego `true` ani `"18240000"` tam, gdzie wymagane są grosze jako liczba całkowita;
- obowiązują reguły zależne od statusu: faktura ze statusem `ok` ma kwotę.

Sprawdza to **zanim** cokolwiek mogłoby uzupełnić wartość domyślną. Brakujące pole i pole ustawione na `null` to dwa różne fakty, a wartość domyślna zatarłaby tę różnicę. Wynik, który łamie kontrakt, to *błąd walidacji lokalnej*, nigdy dowód. Dotyczy to także wyniku, w którym `structuredContent` i kopia tekstowa **się nie zgadzają**: klient nie wie, która z nich jest błędna, więc nie używa żadnej i zachowuje surowe dane do wglądu.

**Cztery sposoby, w jakie może skończyć się wywołanie.** Rozróżniaj je. Tylko pierwszy jest zwykłym wynikiem; pozostałe oznaczają błędy wymagające różnych działań naprawczych:
1. **wynik dziedzinowy** (`no_data`, `not_applicable`, `invalid_request`): zwykły ustrukturyzowany wynik. Narzędzie zadziałało i mówi, co znalazło.
2. **błąd narzędzia** (warstwa `tool`, w komunikatach `[błąd narzędzia]`): serwer odpowiedział z `isError: true` (złe typy argumentów, nieznane narzędzie, wyjątek w narzędziu). Model widzi taki błąd i może spróbować ponownie.
3. **błąd protokołu** (`protocol`, `[błąd protokołu]`): serwer odpowiedział **obiektem błędu** JSON-RPC (nieznana metoda, źle zbudowane żądanie).
4. **awaria transportu** (`transport`, `[błąd transportu]`): **żadnej odpowiedzi** (serwer się zakończył, potok się zerwał, minął limit czasu wywołania). Nie jest to odpowiedź z błędem JSON-RPC — klient nie otrzymał żadnej odpowiedzi.

Do tego dochodzi błąd walidacji lokalnej (`validation`, `[błąd walidacji lokalnej]`) z poprzedniego akapitu: odpowiedź została odebrana, ale jest niezgodna z kontraktem.

**Adnotacje opisują, implementacja wymusza.** `readOnlyHint: true` mówi klientom, że narzędzie niczego nie zmienia. To *twierdzenie*. Prawdziwym czyni je dopiero to, że żadne narzędzie Kovalo *nie może* niczego zapisać, zatwierdzić ani obiecać (możliwość a twierdzenie z Miniprojektu 4). Akceptacje w ogóle nie są narzędziem serwera: zostają w asystencie, gdzie workflow z Miniprojektu 3 zatrzymuje się dla człowieka.

**Jeden właściciel rozmowy.** Końcowy asystent to graf z Miniprojektu 3 z **jednym podmienionym węzłem**: na pytania o dokumenty i dane odpowiada agent z Miniprojektu 4, który korzysta z narzędzi udostępnionych przez MCP. Przed grafem nie ma dodatkowego komponentu kierującego wiadomości na odpowiednie ścieżki (ang. router): każdą wiadomość interpretuje jednokrotnie węzeł `understand`, więc dwa komponenty nie mogą jej różnie zinterpretować. Przy wznowieniu po pauzie nic nie jest rozumiane ponownie. A jeden publiczny punkt wejścia (`assistant_turn`) pilnuje zasady, że wstrzymana rozmowa nie przyjmuje nowej wiadomości.

**Zgodność wyników: to samo wywołanie, dwie ścieżki.** Wywołanie narzędzia bezpośrednio i przez MCP, z tymi samymi argumentami i danymi, musi dać ten sam rekord, pole po polu i **typ po typie** (97 to nie 97.0; grosze to nie złotówki). To sprawdza *połączenie*: nakładki i transport. Nie sprawdza *odpowiedzi biznesowej*: dwie ścieżki, które korzystają z tej samej błędnej funkcji, zgadzają się idealnie. Dlatego odpowiedzi nadal ocenia wzorzec z Miniprojektów 4 i 3.

**Oceniaj każdą turę według jej oczekiwanej ścieżki.** Na pytanie „Kto musi zatwierdzić 22%?” poprawnie odpowiadają reguły z Miniprojektu 3, bez wywołania narzędzia. „Zatwierdź to teraz” poprawnie *zatrzymuje* rozmowę dla człowieka. Gdyby każdą turę oceniać sprawdzeniami agenta z Miniprojektu 4, oba poprawne zachowania zostałyby uznane za błędne. Dlatego wzorzec każdej tury podaje jej oczekiwaną ścieżkę i stosuje się tylko sprawdzenia tej ścieżki. Tura, która poszła złą ścieżką, nadal się liczy. Tura z pytaniem o dane bez zapisu przebiegu agenta to błąd, a nie pominięcie.

**Limity czasu na każdym etapie.** Serwer może się zakończyć, nigdy nie odpowiedzieć, zawiesić się w trakcie wywołania albo zignorować prośbę o zamknięcie. Klient musi zachować kontrolę:
- limit czasu na **start**;
- limit czasu na **każde wywołanie**, po którym wywołanie jest anulowane, a połączenie nie jest używane ponownie;
- ograniczone w czasie **zamykanie połączenia i zwalnianie zasobów**: zamknij stdin, poczekaj, zakończ proces, a w ostateczności wymuś jego zakończenie.

Anulowanie po stronie klienta nie dowodzi, że serwer przestał działać: dowodzi tego dopiero zakończony proces.

**Błąd zaobserwowany w ewaluacji.** W dwóch pierwszych przebiegach angielskiej wersji projektu wiadomości „Submit that.” (po pytaniu o politykę) i „Please try again with the same terms.” (po odrzuceniu) zostały zrozumiane jako wnioski o akceptację, które nie były ani *nowe*, ani *aktualizacją*. Reguła z Miniprojektu 3 słusznie dopytała wtedy, a tura kończyła się błędem. Prompt nigdy nie mówił, czym jest ponowne przesłanie wniosku. Mówi to dopiero własny prompt rozumienia z Miniprojektu 5 („prześlij to”, „spróbuj jeszcze raz”, „te same warunki” to aktualizacje), a zaakceptowany prompt z Miniprojektu 3 się nie zmienił. W naszym przebiegu na polskich danych „Prześlij to.” i „Spróbuj jeszcze raz na tych samych warunkach.” zostały rozpoznane jako aktualizacje, a wszystkie 25 tur przeszło każde sprawdzenie. Wynik dotyczy niewielkiego zestawu przykładów i nie gwarantuje poprawności we wszystkich sytuacjach.

## Na co zwrócić uwagę w wynikach

Nie masz własnych wyników? Skorzystaj z przebiegów referencyjnych w [README](README.md).

1. **`show_mcp.py`.** Jakie elementy podstawowe oferuje serwer i kto korzystałby z każdego z nich?
2. **`run_agent_mcp.py`.** Porównaj wynik z przebiegiem Miniprojektu 4 na bezpośrednich narzędziach, sprawdzenie po sprawdzeniu. Co się zmieniło, gdy zmienił się tylko transport? Co się nie zmieniło (T1)? Czy pobranie OTIF za wszystkie potrzebne miesiące wystarczyło do poprawnej odpowiedzi?
3. **`run_assistant_eval.py`.** Które tury oceniły sprawdzenia z Miniprojektu 4, a które z Miniprojektu 3? Ile wywołań MCP było potrzebnych w 25 turach i dlaczego tak mało?
4. **Błąd.** Wybierz jeden błąd w `mini_project_5/output/assistant_run.json` (albo wywołaj go celowo: zatrzymaj serwer, podaj zły argument). Z której z czterech warstw pochodził?
