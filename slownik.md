# Słownik pojęć biznesowych

Dokumenty Kovalo używają języka dystrybucji, finansów i zarządzania. Ten słownik wyjaśnia skróty i pojęcia, na które trafisz w korpusie (`data/corpus/`), danych firmy (`data/company/`) i miniprojektach. W nawiasach podajemy dokumenty, w których pojęcie występuje. Pojęcia techniczne (LLM, embedding, chunk, agent, MCP…) wyjaśniają pliki CONCEPTS.md poszczególnych miniprojektów.

Wskaźniki Kovalo zdefiniowano w dokumencie FAQ-501. Gdy słownik i FAQ-501 się różnią, rozstrzyga FAQ-501.

## Firma i role

- **sp. z o.o.**: spółka z ograniczoną odpowiedzialnością, najczęstsza forma prawna średnich firm w Polsce. Za długi spółki odpowiada ona sama, a nie jej właściciele.
- **Zarząd**: organ, który kieruje spółką; w Kovalo zbiera się na **posiedzeniach zarządu** (MTG-401).
- **CEO** (ang. Chief Executive Officer): prezes zarządu, najwyższy rangą menedżer firmy.
- **CFO** (ang. Chief Financial Officer): dyrektor finansowy, odpowiada za finanse, płynność i ryzyko. W polityce rabatowej zatwierdza rabaty powyżej 20% (razem z CEO) i rabaty poniżej minimalnej marży (POL-001).
- **Dyrektor handlowy** (ang. Commercial Director): kieruje sprzedażą; zatwierdza rabaty powyżej 12% do 20% włącznie (POL-001).
- **Regionalny kierownik sprzedaży** i **przedstawiciel handlowy**: niższe szczeble działu sprzedaży, z niższymi limitami rabatów (POL-001).
- **Dyrektor operacyjny**: odpowiada za działanie firmy na co dzień (logistyka, magazyny, obsługa); w scenariuszu to sponsor projektu.
- **Key account manager**: opiekun kluczowego klienta albo, jak w MTG-403, osoba po stronie dostawcy odpowiedzialna za współpracę z Kovalo.
- **Sponsor projektu**: menedżer, który zleca projekt, finansuje go i odbiera jego wyniki.

## Klienci i sprzedaż

- **Dystrybutor (hurtownik)**: firma, która kupuje towar od producentów i sprzedaje go dalej sklepom i restauracjom. Kovalo to dystrybutor żywności i napojów.
- **HoReCa** (ang. Hotels, Restaurants, Cafés): hotele, restauracje i kawiarnie jako grupa klientów.
- **Sklepy convenience**: małe sklepy „pod domem”, często w sieciach, otwarte długo i blisko klienta.
- **Klient strategiczny**: jeden z dziesięciu klientów oznaczonych w CRM jako szczególnie ważni; dla nich dyrektor handlowy może zatwierdzić wyższy rabat (POL-001).
- **Cennik (cena cennikowa)**: oficjalna cena pozycji przed rabatem. Rabat liczy się od ceny cennikowej bez VAT (POL-001).
- **Rabat**: obniżka ceny dla klienta, wyrażona w procentach ceny cennikowej. Kto może go zatwierdzić, zależy od jego wysokości (POL-001, Miniprojekt 3).
- **Rabat wolumenowy (retrospektywny)**: rabat zależny od łącznej wartości zakupów w okresie, naliczany po fakcie, np. po zakończeniu roku. W CON-102 przyznaje go dostawca firmie Kovalo. Rabaty wolumenowe zapisane w umowach z klientami nie podlegają polityce rabatowej POL-001, tylko procesowi ustalania warunków kredytowych i handlowych.
- **Oferta konkurencji**: udokumentowana niższa cena innego dostawcy, którą klient pokazuje; uzasadnia wyjątek w polityce rabatowej (POL-001).
- **Wyprzedaż końcówek**: sprzedaż resztek towaru (np. z krótkim terminem przydatności) z dużym rabatem; ma własne zasady akceptacji (POL-001).
- **CRM** (ang. Customer Relationship Management): system do zarządzania relacjami z klientami; Kovalo zapisuje w nim m.in. akceptacje rabatów i klientów strategicznych.
- **Portal B2B** (ang. business-to-business): sklep internetowy dla klientów firmowych.
- **EDI** (ang. Electronic Data Interchange): automatyczna wymiana dokumentów (zamówień, faktur) między systemami firm (PRO-201).
- **Odejścia klientów (ang. churn)**: utrata klientów; **wskaźnik odejść** to klienci utraceni podzieleni przez klientów aktywnych na początku okresu (FAQ-501, REP-302).

## Finanse

- **PLN, złoty, grosz**: polska waluta; 1 PLN = 100 groszy. Dane Kovalo podają kwoty faktur w całkowitych groszach, żeby uniknąć błędów zaokrągleń (Miniprojekt 4).
- **Procent a punkt procentowy (pp)**: różnica między 97% a 94,6% to 2,4 **punktu procentowego**, a nie 2,4%. Kary w umowie z Mleczną Doliną liczy się od pełnych punktów procentowych (CON-101).
- **Sprzedaż netto**: przychody ze sprzedaży po odjęciu rabatów udzielonych klientom, bez VAT (FAQ-501).
- **Marża brutto**: (sprzedaż netto − koszt sprzedanych towarów) / sprzedaż netto. Mówi, ile z każdej złotówki sprzedaży zostaje po zapłaceniu za towar (FAQ-501). Docelowa marża brutto Kovalo to 12,5%.
- **Marża po rabacie** i **minimalna marża**: marża brutto pozycji po udzieleniu rabatu. Gdy spada poniżej 9%, rabat musi dodatkowo zatwierdzić CFO (POL-001).
- **VAT** (podatek od towarów i usług): podatek doliczany do ceny netto; rabaty i marże w Kovalo liczy się bez VAT.
- **Faktura**: dokument sprzedaży z kwotą do zapłaty. **Nota uznaniowa**: dokument, w którym jedna firma uznaje należność drugiej, np. dostawca przyznaje Kovalo bonifikatę za karę umowną; rozlicza się ją z kolejną fakturą (CON-101).
- **Należności (handlowe)**: pieniądze, które klienci są winni firmie za sprzedany towar. **Należności przeterminowane**: niezapłacone po terminie.
- **Termin płatności**: liczba dni od faktury, w ciągu których klient ma zapłacić (POL-002).
- **Limit kredytowy (kupiecki)**: maksymalna kwota, jaką klient może być winien firmie w danym momencie. Wyższe limity wymagają zgody wyższego szczebla, a limit powyżej 150 000 PLN zawsze zgody CFO (POL-002).
- **Windykacja**: odzyskiwanie przeterminowanych należności. W Kovalo konto klienta, który zalega z płatnością ponad 30 dni, jest blokowane dla nowych zamówień, a po 90 dniach sprawa trafia do zewnętrznej firmy windykacyjnej (POL-002).
- **DSO** (ang. Days Sales Outstanding), rotacja należności w dniach: po ilu dniach klienci średnio płacą. Im wyższe, tym więcej pieniędzy jest „zamrożonych” u klientów (FAQ-501, MTG-401).
- **Kapitał obrotowy**: pieniądze zaangażowane w bieżącą działalność (zapasy, należności minus zobowiązania). Wyższe DSO zwiększa potrzebny kapitał obrotowy (MTG-401).
- **Kwartał i półrocze**: II kw. 2026 (ang. Q2) to kwiecień–czerwiec, I półrocze (ang. H1) to styczeń–czerwiec (REP-301, REP-302).

## Dostawy i logistyka

- **Dostawca**: firma, od której Kovalo kupuje towar (np. Mleczna Dolina, Aqua Kryształ). **Podwykonawca logistyczny**: firma, która przewozi towar w imieniu Kovalo (TransBałt, CON-103).
- **OTIF** (ang. on time in full): odsetek dostaw zrealizowanych na czas i w komplecie; jedna brakująca pozycja wystarczy, żeby dostawa nie była „w komplecie” (FAQ-501). W umowach z dostawcami OTIF mierzy się co miesiąc (CON-101, CON-102).
- **Wskaźnik realizacji zamówień (ang. fill rate)**: odsetek zamówionych jednostek, które dotarły; zawsze co najmniej tak wysoki jak składowa „w komplecie” wskaźnika OTIF (FAQ-501).
- **Czas realizacji (ang. lead time)**: czas od potwierdzenia zamówienia do dostawy (CON-101).
- **Okno czasowe dostawy**: uzgodniony przedział godzin, w którym dostawa ma dotrzeć (CON-103).
- **Kara umowna**: kwota, którą strona płaci za niedotrzymanie warunków umowy, np. dostawca za zbyt niski OTIF (CON-101). Jej wysokość zwykle ogranicza **limit** (górny pułap).
- **Rok umowny**: kolejne 12 miesięcy od daty rozpoczęcia umowy (nie musi pokrywać się z rokiem kalendarzowym).
- **Wypowiedzenie umowy**: zakończenie umowy przez jedną ze stron z zachowaniem **okresu wypowiedzenia** (np. 60 dni) albo ze skutkiem natychmiastowym w szczególnych przypadkach (CON-101).
- **CMR**: konwencja o międzynarodowym przewozie drogowym towarów; ogranicza odpowiedzialność przewoźnika za uszkodzony towar (CON-103).
- **Łańcuch chłodniczy**: utrzymywanie wymaganej temperatury produktów chłodzonych od dostawcy do klienta; **odchylenie temperatury** to wyjście poza dozwolony zakres (PRO-203).

## Magazyn i zapasy

- **SKU** (ang. Stock Keeping Unit), indeks towarowy: jedna konkretna pozycja asortymentu, np. woda niegazowana 1,5 l w zgrzewce po 6 sztuk.
- **Inwentaryzacja**: liczenie towaru w magazynie i porównanie wyniku ze stanem w systemie (PRO-202).
- **Analiza ABC**: podział pozycji magazynowych według wartości: A to najcenniejsze (liczone najczęściej), C to najmniej cenne (PRO-202).
- **Ubytki (ang. shrinkage)**: straty zapasów (towar przeterminowany, uszkodzony, zaginiony), wyrażone jako procent sprzedaży netto (FAQ-501).
- **Spisanie w straty (odpis)**: usunięcie wartości zepsutego lub zaginionego towaru z ewidencji i ujęcie jej w kosztach; im wyższa wartość, tym wyższy szczebel zatwierdza, powyżej 25 000 PLN CFO (PRO-202).
- **Rotacja zapasów**: ile razy w roku zapas „obraca się”, czyli jest sprzedawany i uzupełniany (FAQ-501).
- **UDT**: Urząd Dozoru Technicznego; jego uprawnienia są wymagane m.in. do obsługi wózków widłowych (PL-601).

## Zarządzanie

- **KPI** (ang. Key Performance Indicator), kluczowy wskaźnik efektywności: liczba, po której firma ocenia, czy osiąga cele, np. OTIF, marża brutto, DSO (FAQ-501).
- **Polityka** a **procedura**: polityka mówi, *co* wolno i kto decyduje (np. POL-001 o rabatach); procedura opisuje, *jak* krok po kroku coś wykonać (np. PRO-202 o inwentaryzacji).
- **Komitet cenowy**: zespół, który decyduje o cenach i rabatach dla grup produktów (MTG-402).
- **Przegląd z dostawcą (przegląd biznesowy)**: regularne spotkanie, na którym strony omawiają wyniki współpracy, np. OTIF (MTG-403, CON-102).
- **Przetarg** i **wdrażanie dostawcy (ang. onboarding)**: zbieranie ofert od kilku dostawców przed wyborem oraz przygotowanie nowego dostawcy do współpracy (POL-005).
- **Proces akceptacji**: ustalona ścieżka zatwierdzania decyzji, np. rabatu przez kolejne osoby zatwierdzające; w Miniprojekcie 3 modeluje go workflow z pauzami.
