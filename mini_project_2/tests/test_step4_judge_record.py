from helpers.records import Verdict
from mini_project_2.src.step4_judge_record import judge_record
from mini_project_2.tests.conftest import FakeStructuredLLM, gold, record


def test_judge_prompt_holds_everything_it_needs():
    llm = FakeStructuredLLM(Verdict(correct=True, grounded=True, reason="Podaje CFO."))
    rec = record("Zatwierdza CFO [TST-001].", ["TST-001"], context_text="Wyjazdy zagraniczne wymagają zgody CFO.")
    g = gold(reference="Wzorzec: wyjazdy zagraniczne zatwierdza CFO.")
    v = judge_record(rec, g, llm)
    assert v == {"correct": True, "grounded": True, "reason": "Podaje CFO.", "error": None}
    assert llm.schemas == [Verdict], "użyj structured output z gotowym schematem Verdict"
    prompt = llm.prompts[0]
    for part, name in [(rec.question, "pytanie"), ("Wyjazdy zagraniczne wymagają zgody CFO.", "zapisany kontekst"),
                       ("Zatwierdza CFO [TST-001].", "odpowiedź"), (g.reference, "odpowiedź wzorcową")]:
        assert part in prompt, f"prompt sędziego musi zawierać {name}"


def test_only_answered_records_are_judged():
    llm = FakeStructuredLLM(Verdict(correct=True, grounded=True, reason="x"))
    empty = {"correct": None, "grounded": None, "reason": None, "error": None}
    assert judge_record(record("Brak tej informacji w dokumentach.", answerable=False), gold(), llm) == empty
    assert judge_record(record(error="bad JSON"), gold(), llm) == empty
    assert llm.prompts == [], "nie wywołuj LLM-a dla odmów ani nieudanych rekordów"


def test_a_judge_failure_is_recorded_not_raised():
    v = judge_record(record("CFO.", ["TST-001"]), gold(), FakeStructuredLLM(error=ValueError("bad JSON")))
    assert v["error"] and v["correct"] is None
    v = judge_record(record("CFO.", ["TST-001"]), gold(), FakeStructuredLLM(result=None))
    assert v["error"] and v["correct"] is None
