# Scenariusz biznesowy: Kovalo Distribution

## Firma

**Kovalo Distribution sp. z o.o.** to regionalny dystrybutor żywności i napojów z siedzibą w Łodzi. Zaopatruje się u około 140 dostawców (nabiał, woda butelkowana, napoje, przekąski, artykuły suche) i obsługuje około 1400 klientów detalicznych: niezależne sklepy spożywcze, sieci sklepów convenience i sektor HoReCa (hotele, restauracje, kawiarnie).

| Fakt | Wartość |
|---|---|
| Magazyny | Łódź (centrala), Poznań, Gdańsk |
| Pracownicy | około 220, w tym 70 kierowców |
| Sprzedaż netto w 2025 r. | około 180 mln PLN |
| Aktywni klienci | około 1400 |
| Docelowa marża brutto | 12,5% |

Marże w dystrybucji są niskie. Utratę jednego punktu procentowego marży, spóźnienia dostawcy nabiału czy serię rabatów udzielonych bez zgody widać w wynikach kwartalnych już po kilku tygodniach.

## Problem

Kadra zarządzająca codziennie podejmuje dziesiątki drobnych decyzji. Czy możemy udzielić 15-procentowego rabatu? Czy nasz dostawca nabiału łamie umowę? Dlaczego w Gdańsku ubywa klientów? Co komitet cenowy postanowił w sprawie wody?

Potrzebne informacje są dostępne, ale rozproszone w politykach firmy, umowach z dostawcami, procedurach, notatkach ze spotkań i raportach kwartalnych. Menedżerowie albo przez dwadzieścia minut przeszukują dyski sieciowe, albo odpowiadają z pamięci. Właśnie tak regionalny kierownik sprzedaży zatwierdził kiedyś rabat, który według polityki wymagał zgody dyrektora handlowego.

## Twoja rola

Dołączasz jako **inżynier sztucznej inteligencji (AI)** do niewielkiego zespołu odpowiedzialnego za cyfryzację Kovalo. Podlegasz **dyrektorowi operacyjnemu**, który jest sponsorem projektu:

> „Nie chcę kolejnego dashboardu. Chcę asystenta, którego zapytam normalnym językiem, który odpowie na podstawie *naszych* dokumentów, pokaże, skąd ma odpowiedź, i pomoże mi podjąć decyzję. A zanim dam go czterdziestu menedżerom, muszę wiedzieć, ile będzie kosztował”.

## System, który zbudujesz: Kovalo Decision Copilot

W pięciu miniprojektach zbudujesz jeden system. Najpierw podzielisz dokumenty na fragmenty (ang. chunks) i utworzysz ich reprezentacje wektorowe (ang. embeddings). Następnie połączysz wyszukiwanie z generowaniem odpowiedzi (ang. retrieval-augmented generation, RAG), dodasz przepływ pracy (ang. workflow) i zintegrujesz narzędzia przez protokół MCP (ang. Model Context Protocol):

```
 Miniprojekt 1  Fundament wiedzy         dokumenty -> tokeny -> chunki -> embeddingi -> wyszukiwanie semantyczne
 Miniprojekt 2  Odpowiedzi ze źródłami   retrieval-augmented generation + ewaluacja
 Miniprojekt 3  Workflow decyzyjny       workflow w LangGraph, który rozpoznaje sprawę, stosuje reguły i prosi o akceptację
 Miniprojekt 4  Agent z narzędziami      agent korzystający z dokumentów i danych firmy
 Miniprojekt 5  Integracja               narzędzia udostępnione przez MCP i końcowy asystent
```

Każdy miniprojekt ma własny folder (`mini_project_1/` … `mini_project_5/`) i korzysta z kodu poprzednich. Wyszukiwanie z Miniprojektu 1 to fundament: z niego korzystają wszystkie późniejsze kroki.

## Korpus dokumentów

Zbiór dokumentów (korpus) w folderze `data/corpus/` obejmuje 18 wewnętrznych dokumentów Kovalo w plikach Markdown. Ich metadane zawiera plik `data/corpus/catalog.csv`, po jednym wierszu na dokument (identyfikator, plik, tytuł, typ, dział, właściciel, data wejścia w życie, język):

| Typ | Przykłady |
|---|---|
| `policy` | akceptacja rabatów, limity kredytowe i terminy płatności, zwroty, wybór dostawców |
| `contract` | umowy z dostawcami (nabiał, woda butelkowana), podwykonawca logistyczny |
| `procedure` | od zamówienia do dostawy, inwentaryzacja, incydenty w łańcuchu chłodniczym, regulamin magazynu w Gdańsku (po angielsku) |
| `report` | przegląd operacyjny za II kwartał 2026 r., analiza odejść klientów |
| `meeting_notes` | posiedzenie zarządu, komitet cenowy, spotkanie z dostawcą |
| `faq` | definicje KPI |

Dokumenty są ze sobą spójne: notatki ze spotkań odwołują się do polityk, a raporty przytaczają zapisy umów. Kolejne miniprojekty z tego korzystają. Jeden dokument, regulamin magazynu w Gdańsku, jest celowo po angielsku: na nim sprawdzisz, jak wyszukiwanie radzi sobie z pytaniem w innym języku niż dokument.

Nie znasz któregoś skrótu albo pojęcia biznesowego? Zajrzyj do [słownika pojęć biznesowych](slownik.md).

---

*Kovalo Distribution oraz wszystkie dokumenty, osoby i liczby w tym projekcie są fikcyjne i powstały w celach edukacyjnych.*
