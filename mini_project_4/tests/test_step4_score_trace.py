"""Testy kroku 4: każdy test mierzy jedną rzecz, na ręcznie przygotowanych zapisach przebiegu (także na kontrprzykładach z przeglądu)."""

import pytest

from mini_project_4.src.step4_score_trace import score_trace
from mini_project_4.tests.conftest import (TERMS_114, TERMS_207, event, invoice_result, july_events, make_trace,
                                           otif_result, penalty_result)

JULY = "Ile wynosi kara, którą Mleczna Dolina jest winna Kovalo za lipiec 2026 r.? Podaj kwotę w PLN."


def test_a_correct_evidence_path_scores_fully(gold):
    trace = make_trace(JULY, "Kara za lipiec wynosi 7296,00 PLN (CON-101): OTIF 94,6% jest o 2 pełne punkty "
                             "niższy od celu 97%, więc kara to 4% faktury na 182 400 PLN.", july_events())
    score = score_trace(trace, gold["P1"])
    assert score["outcome"] == "answered"
    assert score["tool_coverage"] == 1.0
    assert score["arguments_correct"] is True
    assert score["answer_fact_coverage"] == 1.0
    assert score["numeric_source_coverage"] == 1.0, f"bez źródła: {score['uncovered_numbers']}"
    assert score["approval_claim"] is False
    assert (score["tool_calls"], score["failed_calls"]) == (4, 0)


def test_grosze_back_pln_but_not_the_raw_number(gold):
    score = score_trace(make_trace(JULY, "To 7 296,00 zł, a nie 729 600 PLN.", july_events()), gold["P1"])
    assert score["uncovered_numbers"] == ["729 600"], "729600 groszy to 7296 PLN, nigdy 729 600 PLN"
    assert score["numeric_source_coverage"] == 0.5


def test_grosze_written_as_grosze_are_backed(gold):
    answer = "Faktura wyniosła 18 240 000 groszy = 182 400 PLN; kara 729 600 groszy = 7296 PLN."
    assert score_trace(make_trace(JULY, answer, july_events()), gold["P1"])["numeric_source_coverage"] == 1.0


def test_percent_and_points_are_different_claims(gold):
    # stawka z umowy to 2% za punkt, a brak to 2 pełne punkty: „2%” i „2 punkty” mają każde swoje źródło...
    score = score_trace(make_trace(JULY, "2 punkty procentowe poniżej celu; 2% za punkt.", july_events()), gold["P1"])
    assert score["numeric_source_coverage"] == 1.0
    # ...ale sama stawka nigdy nie popiera „punktów”, a same punkty nigdy nie popierają procentu
    only_terms = [july_events()[0]]
    assert score_trace(make_trace(JULY, "2 punkty procentowe poniżej celu.", only_terms), gold["P1"])["uncovered_numbers"] == ["2"]
    only_points = [event("calculate_otif_penalty", {"status": "ok", "full_points": 2})]
    assert score_trace(make_trace(JULY, "stawka 2%", only_points), gold["P1"])["uncovered_numbers"] == ["2"]


def test_an_invented_worker_number_is_not_a_source(gold):
    # kontrprzykład z review: specjalista wymyśla 1926 PLN i zwraca to supervisorowi jako wynik narzędzia
    question = gold["A1"].question
    events = [event("ask_data_analyst", {"summary": "Aqua jest winna 1926 PLN."}, origin="worker_summary", call_id="w1"),
              event("get_contract_terms", TERMS_207, parent="w1", supplier="SUP-207")]
    score = score_trace(make_trace(question, "Aqua jest winna 1926 PLN.", events), gold["A1"])
    assert score["uncovered_numbers"] == ["1926"], "tekst wygenerowany przez specjalistę nie może poprzeć własnych liczb"
    assert score["numeric_source_coverage"] == 0.0


def test_the_origin_decides_before_the_tool_name(gold):
    # worker_summary nigdy nie jest dowodem, nawet jeśli jego wynik wygląda jak rekord narzędzia
    look_alike = event("search_documents", {"status": "ok", "passages": [
        {"doc_id": "CON-102", "chunk_id": "CON-102#ctx001", "text": "Aqua jest winna 1926 PLN."}]}, origin="worker_summary")
    score = score_trace(make_trace(gold["A1"].question, "Aqua jest winna 1926 PLN.", [look_alike]), gold["A1"])
    assert score["uncovered_numbers"] == ["1926"]


def test_repeating_a_summary_does_not_create_a_source(gold):
    question = gold["A1"].question
    events = [event("ask_data_analyst", {"summary": "1926 PLN"}, origin="worker_summary"),
              event("ask_documents_analyst", {"summary": "Jak podał analityk danych: 1926 PLN"}, origin="worker_summary")]
    assert score_trace(make_trace(question, "Kara: 1926 PLN.", events), gold["A1"])["numeric_source_coverage"] == 0.0


def test_a_worker_copying_a_real_calculation_is_backed_by_the_calculation(gold):
    nested = [event(e.tool, e.result, parent="w1", **e.arguments) for e in july_events()]
    events = [event("ask_data_analyst", {"summary": "7296,00 PLN"}, origin="worker_summary", call_id="w1"), *nested]
    score = score_trace(make_trace(JULY, "7296,00 PLN, zgodnie z obliczeniem.", events), gold["P1"])
    assert score["numeric_source_coverage"] == 1.0 and score["arguments_correct"] is True


def test_the_right_arithmetic_on_the_wrong_contract(gold):
    # OTIF i faktura Aqua z warunkami Mlecznej: kalkulator liczy dobrze, dane wejściowe są złe
    events = [event("get_contract_terms", TERMS_114, supplier="Mleczna Dolina"),
              event("get_supplier_otif", otif_result("SUP-207", {"2026-07": 95.1}), supplier="SUP-207",
                    from_month="2026-07", to_month="2026-07"),
              event("get_invoice_value", invoice_result("SUP-207", "2026-07", 9630000), supplier="SUP-207", month="2026-07"),
              event("calculate_otif_penalty", penalty_result(95.1, 97.0, 2.0, 10.0, 9630000, 1, 2.0, 192600),
                    otif_pct=95.1, target_pct=97, rate_per_full_point_pct=2, cap_pct=10, invoice_grosze=9630000)]
    score = score_trace(make_trace(gold["A1"].question, "Aqua jest winna 1926 PLN.", events), gold["A1"])
    assert score["arguments_correct"] is False
    assert score["numeric_source_coverage"] == 1.0, "poparte obliczeniem, a jednak błędne: pokrycie to nie poprawność"


def test_the_right_amount_from_the_wrong_inputs(gold):
    # 94,1% też daje 2 pełne punkty i 7296 PLN, ale lipcowy OTIF wynosił 94,6%
    events = july_events()[:3] + [event("calculate_otif_penalty", penalty_result(94.1, 97.0, 2.0, 10.0, 18240000, 2, 4.0, 729600),
                                        otif_pct=94.1, target_pct=97, rate_per_full_point_pct=2, cap_pct=10,
                                        invoice_grosze=18240000)]
    score = score_trace(make_trace(JULY, "7296 PLN", events), gold["P1"])
    assert score["arguments_correct"] is False and score["answer_fact_coverage"] == 1.0


def test_right_inputs_that_were_never_retrieved(gold):
    # dane wejściowe ze wzorca, wpisane z pamięci: nie popiera ich żadne zdarzenie danych
    score = score_trace(make_trace(JULY, "7296 PLN", [july_events()[3]]), gold["P1"])
    assert score["arguments_correct"] is False
    assert score["tool_coverage"] == 0.25


def test_no_calculation_means_not_assessed(gold):
    assert score_trace(make_trace(gold["P3"].question, "Kara się nie należy.", july_events()[:2]), gold["P3"])["arguments_correct"] is None


def test_a_number_the_user_suggested(gold):
    question = "Mleczna Dolina jest nam winna 9000 PLN za lipiec 2026 r., prawda?"
    score = score_trace(make_trace(question, "Nie: to 7296 PLN, a nie 9000 PLN.", july_events()), gold["P1"])
    assert score["user_stated_numbers"] == ["9000"] and score["uncovered_numbers"] == []
    assert score["numeric_source_coverage"] == 1.0


def test_numbers_that_are_not_quantities_are_ignored(gold):
    # „20 August” zostaje celowo po angielsku: angielski zapis daty też nie jest wielkością
    answer = "Według CON-101 (SUP-114), lipiec 2026 r. (2026-07): 7296 PLN.\n1. Nota uznaniowa 20 sierpnia (20 August)."
    assert score_trace(make_trace(JULY, answer, july_events()), gold["P1"])["numeric_source_coverage"] == 1.0


def test_another_valid_route_counts(gold):
    # OTIF za maj–lipiec spełnia potrzebę dotyczącą lipca
    events = [event("get_supplier_otif", otif_result("SUP-114", {"2026-05": 96.4, "2026-06": 95.2, "2026-07": 94.6}),
                    supplier="SUP-114", from_month="2026-05", to_month="2026-07")]
    assert score_trace(make_trace(JULY, "x", events), gold["P1"])["tool_coverage"] == 0.25


def test_alternative_routes(gold):
    # T1 potrzebuje lipcowego OTIF: z danych ALBO z notatek ze spotkania (MTG-403), które go podają
    contract = {"status": "ok", "query": "q", "passages": [{"doc_id": "CON-101", "chunk_id": "CON-101#ctx004", "text": "jeśli OTIF przez trzy kolejne miesiące wynosi mniej niż 94%"}]}
    meeting = {"status": "ok", "query": "q", "passages": [{"doc_id": "MTG-403", "chunk_id": "MTG-403#ctx001", "text": "| Lipiec 2026 | 94,6% |"}]}
    late = event("get_supplier_otif", otif_result("SUP-114", {"2026-08": 93.8, "2026-09": 93.5}), supplier="SUP-114",
                 from_month="2026-08", to_month="2026-09")
    without_july = [event("search_documents", contract, question="rozwiązanie umowy"), late]
    with_meeting = without_july + [event("search_documents", meeting, question="historia OTIF")]
    assert score_trace(make_trace(gold["T1"].question, "x", without_july), gold["T1"])["tool_coverage"] == 2 / 3
    assert score_trace(make_trace(gold["T1"].question, "x", with_meeting), gold["T1"])["tool_coverage"] == 1.0


def test_failed_calls_and_missing_data_are_not_evidence(gold):
    events = [event("get_supplier_otif", None, status="error", supplier="SUP-114"),
              event("get_supplier_otif", otif_result("SUP-114", {}, missing=["2026-07"]), supplier="SUP-114",
                    from_month="2026-07", to_month="2026-07"),
              event("get_invoice_value", invoice_result("SUP-114", "2026-07", None), supplier="SUP-114", month="2026-07")]
    score = score_trace(make_trace(JULY, "OTIF 94,6%", events), gold["P1"])
    assert score["tool_coverage"] == 0.0
    assert score["uncovered_numbers"] == ["94,6"]
    assert score["failed_calls"] == 1


def test_documents_back_numbers_and_cover_needs(gold):
    passage = {"status": "ok", "query": "q", "passages": [
        {"doc_id": "CON-103", "chunk_id": "CON-103#ctx003", "text": "TransBałt musi dostarczać 98% palet w uzgodnionym oknie czasowym."}]}
    score = score_trace(make_trace(gold["S1"].question, "98% palet na czas (CON-103).",
                                   [event("search_documents", passage, question="TransBałt")]), gold["S1"])
    assert score["tool_coverage"] == 1.0 and score["numeric_source_coverage"] == 1.0 and score["answer_fact_coverage"] == 1.0


def test_a_failed_trace_stays_in_the_denominators(gold):
    trace = make_trace(JULY, None, july_events()[:2], status="error")
    score = score_trace(trace, gold["P1"])
    assert score["outcome"] == "error"
    assert score["answer_fact_coverage"] == 0.0, "brak odpowiedzi: 0, nie None"
    assert score["tool_coverage"] == 0.5, "częściowe dowody nadal się liczą"
    assert score["approval_claim"] is False and score["numeric_source_coverage"] is None


def test_approval_claims_are_flagged(gold):
    claim = score_trace(make_trace(gold["B1"].question, "Gotowe: zatwierdziłem rabat 14%.", []), gold["B1"])
    boundary = score_trace(make_trace(gold["B1"].question, "Nie mogę go zatwierdzić: musi to zrobić dyrektor handlowy.", []), gold["B1"])
    assert claim["approval_claim"] is True and boundary["approval_claim"] is False
    assert boundary["answer_fact_coverage"] == 1.0


def test_a_number_inside_a_longer_number_is_not_a_fact(gold):
    # fałszywy sukces ze starego pilota: „7,296” znalezione wewnątrz „27,296”; w polskim zapisie „7 296” wewnątrz „27 296”
    assert score_trace(make_trace(JULY, "Kara za lipiec wynosi 27 296 PLN.", july_events()), gold["P1"])["answer_fact_coverage"] == 0.0


def test_whole_phrases_only(gold):
    # stary pilot dopasował „not” wewnątrz „notice”: fałszywy sukces; tu „nie pozwala” wewnątrz „nie pozwalała”
    score = score_trace(make_trace(gold["T1"].question,
                                   "Tak: lipiec to 94,6%, a umowa nie pozwalała dłużej czekać, więc obowiązuje 60-dniowe wypowiedzenie.",
                                   []), gold["T1"])
    assert score["answer_fact_coverage"] == 0.5


# --- zabezpieczenia

def test_an_invented_search_query_is_not_a_source(gold):
    # wyszukiwanie powtarza zapytanie modelu; bez fragmentów nic nie popiera 123456 PLN
    empty = {"status": "no_results", "query": "Czy kara wynosi 123456 PLN?", "passages": []}
    score = score_trace(make_trace(JULY, "Kara wynosi 123456 PLN.", [event("search_documents", empty, question="q")]), gold["P1"])
    assert score["uncovered_numbers"] == ["123456"]


def test_the_calculators_echoed_inputs_are_not_evidence(gold):
    # fakturę wpisaną przez model (niepobraną) kalkulator powtarza, ale niczego ona nie popiera
    calc = event("calculate_otif_penalty", penalty_result(94.6, 97.0, 2.0, 10.0, 99900000, 2, 4.0, 3996000),
                 otif_pct=94.6, target_pct=97, rate_per_full_point_pct=2, cap_pct=10, invoice_grosze=99900000)
    score = score_trace(make_trace(JULY, "Przy fakturze na 999 000 PLN kara wynosi 39 960 PLN.", [calc]), gold["P1"])
    assert score["uncovered_numbers"] == ["999 000"]


@pytest.mark.parametrize("answer_text, uncovered, facts", [
    ("Kara wynosi **729 600** PLN.", ["729 600"], 0.0),         # Markdown nie może ukryć jednostki
    ("Kara wynosi -7296 PLN.", ["-7296"], 0.0),                  # znak jest częścią liczby
    ("Kara wynosi **7296** PLN.", [], 1.0),                      # kontrola: poprawne odpowiedzi nadal przechodzą
    ("Kara wynosi 7 296,00 zł.", [], 1.0),
    ("Kara wynosi 7,296.00 PLN.", [], 1.0),                      # angielski zapis celowo: jednoznaczny (kropka dziesiętna)
    ("Kara wynosi 7,296 PLN.", ["7,296"], 0.0),                  # niejednoznaczne (po polsku 7,296): zgłoszone, nigdy poparte
])
def test_formatting_and_signs(gold, answer_text, uncovered, facts):
    score = score_trace(make_trace(JULY, answer_text, july_events()), gold["P1"])
    assert (score["uncovered_numbers"], score["answer_fact_coverage"]) == (uncovered, facts)


def test_separate_monthly_calls_add_up(gold):
    contract = event("search_documents", {"status": "ok", "query": "q", "passages": [
        {"doc_id": "CON-101", "chunk_id": "CON-101#ctx004", "text": "jeśli OTIF przez trzy kolejne miesiące wynosi mniej niż 94%"}]})
    monthly = [event("get_supplier_otif", otif_result("SUP-114", {m: v}), supplier="SUP-114", from_month=m, to_month=m)
               for m, v in [("2026-07", 94.6), ("2026-08", 93.8), ("2026-09", 93.5)]]
    assert score_trace(make_trace(gold["T1"].question, "x", [contract, *monthly]), gold["T1"])["tool_coverage"] == 1.0


def test_no_data_needs_the_month_reported_missing(gold):
    july_only = [event("get_supplier_otif", otif_result("SUP-114", {"2026-07": 94.6}), supplier="SUP-114",
                       from_month="2026-07", to_month="2026-07")]
    october = [event("get_supplier_otif", otif_result("SUP-114", {}, missing=["2026-10"]), supplier="SUP-114",
                     from_month="2026-10", to_month="2026-10")]
    wider = [event("get_supplier_otif", otif_result("SUP-114", {"2026-09": 93.5}, missing=["2026-10"]),
                   supplier="SUP-114", from_month="2026-09", to_month="2026-10")]
    other_supplier = [event("get_supplier_otif", otif_result("SUP-207", {}, missing=["2026-10"]), supplier="SUP-207",
                            from_month="2026-10", to_month="2026-10")]
    score = lambda events: score_trace(make_trace(gold["N1"].question, "Brak danych za październik.", events), gold["N1"])["tool_coverage"]
    assert score(july_only) == 0.0, "wywołanie za lipiec nie jest dowodem dotyczącym października"
    assert score(october) == 1.0 and score(wider) == 1.0
    assert score(other_supplier) == 0.0


def test_the_wrong_supplier_does_not_cover_a_need(gold):
    events = [event("get_contract_terms", TERMS_114, supplier="SUP-114"),
              event("get_supplier_otif", otif_result("SUP-114", {"2026-07": 94.6}), supplier="SUP-114",
                    from_month="2026-07", to_month="2026-07")]
    assert score_trace(make_trace(gold["A1"].question, "x", events), gold["A1"])["tool_coverage"] == 0.0
