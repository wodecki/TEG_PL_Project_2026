from mini_project_2.src.step3_score_record import score_record
from mini_project_2.tests.conftest import gold, record


def test_a_correct_cited_answer():
    s = score_record(record("CFO zatwierdza wyjazdy zagraniczne [TST-001].", ["TST-001"]), gold())
    assert s["outcome"] == "answered"
    assert s["evidence_phrase_coverage"] == 1.0 and s["answer_coverage"] == 1.0
    assert s["citations_present"] and s["citations_valid"] and s["cites_relevant"]
    assert s["refusal"] is None


def test_facts_match_whole_words_and_numbers_only():
    g = gold(key_facts=[["9%"], ["zarząd"]])
    assert score_record(record("Minimalna marża to 19%; decyzja należy do zarządu.", ["TST-001"]), g)["answer_coverage"] == 0.0, \
        "„9%” nie może pasować wewnątrz „19%”, a „zarząd” wewnątrz „zarządu”"
    assert score_record(record("Minimalna marża to 19,9% albo 1.9% (decydują zarządy).", ["TST-001"]), g)["answer_coverage"] == 0.0, \
        "„9%” nie może pasować wewnątrz „19,9%” ani „1.9%”"
    assert score_record(record("Poniżej  9%.  Decyduje (ZARZĄD).", ["TST-001"]), g)["answer_coverage"] == 1.0, \
        "pomiń wielkość liter i dodatkowe spacje; zwykła interpunkcja wokół faktu nie przeszkadza"
    grouped = gold(key_facts=[["500,000 PLN"]])
    assert score_record(record("Powyżej 1,500,000 PLN.", ["TST-001"]), grouped)["answer_coverage"] == 0.0, \
        "„500,000 PLN” nie może pasować wewnątrz „1,500,000 PLN”"
    spaced = gold(key_facts=[["500 000 PLN"]])
    assert score_record(record("Powyżej 1 500 000 PLN.", ["TST-001"]), spaced)["answer_coverage"] == 0.0, \
        "„500 000 PLN” nie może pasować wewnątrz „1 500 000 PLN”"
    assert score_record(record("Powyżej 500 000 PLN rocznie.", ["TST-001"]), spaced)["answer_coverage"] == 1.0


def test_negation_is_a_known_limitation():
    """Pokrycie kluczowych faktów to nie poprawność: „nie CFO” nadal zawiera „CFO”. Sędzia LLM (krok 4) to zauważy."""
    assert score_record(record("Nie CFO; zatwierdza CEO.", ["TST-001"]), gold())["answer_coverage"] == 1.0


def test_citation_rules():
    assert score_record(record("CFO.", []), gold())["citations_present"] is False
    assert score_record(record("CFO.", []), gold())["citations_valid"] is False, "brak odwołania to nie jest prawidłowe odwołanie"
    s = score_record(record("CFO.", ["TST-009"]), gold())
    assert s["citations_valid"] is False and s["cites_relevant"] is False, "TST-009 nie było w kontekście"


def test_error_never_earns_answer_or_refusal_credit():
    s = score_record(record(error="OutputParserException: bad JSON"), gold(answerable=False, key_facts=[], evidence_facts=[]))
    assert s["outcome"] == "error"
    assert all(v is None for k, v in s.items() if k != "outcome"), "błąd nie dostaje punktów za odmowę, odpowiedź ani odwołania"


def test_evidence_does_not_depend_on_generation():
    """Dowody opisują znaleziony tekst: ten sam kontekst daje tę samą ocenę dowodów, z błędem czy bez."""
    ok = score_record(record("CFO.", ["TST-001"]), gold())
    failed = score_record(record(error="APIError: timeout"), gold())
    assert failed["evidence_phrase_coverage"] == ok["evidence_phrase_coverage"] == 1.0
    assert failed["answer_coverage"] is None and failed["citations_valid"] is None


def test_refusals():
    unanswerable = gold(answerable=False, relevant_docs=[], key_facts=[], evidence_facts=[])
    assert score_record(record("Brak tej informacji w dokumentach.", answerable=False), unanswerable)["refusal"] == "correct"
    assert score_record(record("To 9000 PLN.", ["TST-001"]), unanswerable)["refusal"] == "missed"
    no_evidence = record("Brak tej informacji w dokumentach.", answerable=False, context_text="Zasady floty dla furgonetek.")
    s = score_record(no_evidence, gold())
    assert s["evidence_phrase_coverage"] == 0.0 and s["refusal"] == "phrases_missing", "odmowa przy brakujących frazach dowodowych"
    assert score_record(record("Brak tej informacji w dokumentach.", answerable=False), gold())["refusal"] == "phrases_present"


def test_relationship_phrases_avoid_loose_matches():
    """Dowód zapisany jako relacja (wiersz tabeli) nie daje się zwieść tym samym słowom w niezwiązanym tekście."""
    g = gold(evidence_facts=[["powyżej 25 000 PLN | CFO"]], key_facts=[["CFO"]])
    unrelated = record("Brak tej informacji w dokumentach.", answerable=False,
                       context_text="Podróże powyżej 25 000 PLN rocznie zgłasza się CFO.")
    assert score_record(unrelated, g)["evidence_phrase_coverage"] == 0.0
    table = record("CFO.", ["TST-001"], context_text="| 5000 do 25 000 PLN | Kierownik finansowy |\n| powyżej 25 000 PLN | CFO |")
    assert score_record(table, g)["evidence_phrase_coverage"] == 1.0


def test_alternative_evidence_paths():
    """W stylu M02: jako dowód liczy się też wprost podany wynik, nie tylko surowa liczba."""
    g = gold(evidence_facts=[["94,6%", "dwa pełne punkty"], ["za każdy pełny punkt procentowy"]], key_facts=[["4%"]])
    text = "2% za każdy pełny punkt procentowy poniżej celu. Lipiec: dwa pełne punkty, 4%."
    assert score_record(record("4% [TST-001]", ["TST-001"], context_text=text), g)["evidence_phrase_coverage"] == 1.0


def test_unanswerable_questions_have_no_evidence_coverage():
    unanswerable = gold(answerable=False, relevant_docs=[], key_facts=[], evidence_facts=[])
    assert score_record(record("Brak tej informacji w dokumentach.", answerable=False), unanswerable)["evidence_phrase_coverage"] is None
