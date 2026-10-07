from helpers.records import Answer, RunRecord
from mini_project_2.src.step2_answer_question import answer_question
from mini_project_2.tests.conftest import TOY_CHUNKS, FakeStructuredLLM

QUESTION = "Kto zatwierdza wyjazdy zagraniczne?"


def test_record_holds_the_context_the_model_saw(toy_store, config):
    llm = FakeStructuredLLM(Answer(answer="CFO.", citations=["TST-001"], answerable=True))
    rec = answer_question(QUESTION, toy_store, llm, config)
    assert isinstance(rec, RunRecord), "answer_question musi zwracać RunRecord (helpers/records.py)"
    assert rec.question == QUESTION and rec.error is None
    texts = {c.page_content for c in TOY_CHUNKS}
    assert rec.context and all(item.text in texts for item in rec.context), "context = dokładny tekst znalezionych chunków"
    assert {item.chunk_id for item in rec.context} <= {c.metadata["chunk_id"] for c in TOY_CHUNKS}
    assert llm.schemas == [Answer], "poproś o structured output z gotowym schematem Answer"


def test_prompt_uses_the_answer_system_and_doc_ids(toy_store, config):
    llm = FakeStructuredLLM(Answer(answer="x", citations=[], answerable=True))
    answer_question(QUESTION, toy_store, llm, config)
    prompt = llm.prompts[0]
    assert config.get("prompts.answer_system").strip()[:40] in prompt, "użyj config.get('prompts.answer_system')"
    assert "[TST-001]" in prompt and "[TST-002]" in prompt, "każdy blok kontekstu zaczyna się od swojego [doc_id] (build_prompt)"
    assert QUESTION in prompt


def test_citations_are_normalised(toy_store, config):
    llm = FakeStructuredLLM(Answer(answer="x", citations=["[TST-001]", " tst-002 ", "TST-001#ctx000"], answerable=True))
    rec = answer_question(QUESTION, toy_store, llm, config)
    assert rec.output.citations == ["TST-001", "TST-002"], \
        f"sprowadź do samych id dokumentów, usuń duplikaty, zachowaj kolejność; jest {rec.output.citations}"


def test_a_model_failure_becomes_an_error_not_an_exception(toy_store, config):
    rec = answer_question(QUESTION, toy_store, FakeStructuredLLM(error=ValueError("bad JSON")), config)
    assert rec.output is None and rec.error, "nieudane wywołanie modelu musi dać output=None i komunikat w error"
    assert rec.context, "kontekst i tak jest zapisany"
    rec = answer_question(QUESTION, toy_store, FakeStructuredLLM(result=None), config)
    assert rec.output is None and rec.error, "brak obiektu Answer od modelu to też błąd"


def test_unknown_ids_are_not_repaired(toy_store, config):
    llm = FakeStructuredLLM(Answer(answer="x", citations=["TST-0019", "XTST-001", "TST-001"], answerable=True))
    rec = answer_question(QUESTION, toy_store, llm, config)
    assert rec.output.citations == ["TST-0019", "XTST-001", "TST-001"], \
        f"normalizuj tylko dokładne formy id; pozostałe zostają bez zmian (i dalej są nieprawidłowe); jest {rec.output.citations}"
