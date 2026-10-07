"""Gotowe: opcjonalne porównanie z DeepEval uznaje za wierne źródłom tylko twierdzenia POPARTE kontekstem
(offline, sędzia ze scenariuszem przez prawdziwą metrykę). Pomijane bez dodatku: uv sync --extra deepeval."""

import asyncio

import pytest

pytest.importorskip("deepeval")

from deepeval.models import DeepEvalBaseLLM  # noqa: E402
from deepeval.test_case import LLMTestCase  # noqa: E402

from mini_project_2.src.compare_with_deepeval import METRIC_CONFIG, evidence, format_examples, make_metrics  # noqa: E402


class ScriptedJudge(DeepEvalBaseLLM):
    """Zwraca ustalone twierdzenia i werdykty: bez sieci, bez klucza."""

    def __init__(self, second_verdict: str):
        self.second_verdict = second_verdict
        super().__init__(model="offline-scripted")

    def load_model(self):
        return self

    def get_model_name(self):
        return "offline-scripted"

    def generate(self, prompt, schema=None, **kwargs):
        values = {"Truths": {"truths": ["Wyjazdy zagraniczne wymagają zgody CFO."]},
                  "Claims": {"claims": ["Wyjazdy zagraniczne wymagają zgody CFO.", "Limit za hotel to 500 PLN za noc."]},
                  "Verdicts": {"verdicts": [{"verdict": "yes"},
                                            {"verdict": self.second_verdict, "reason": "kontekst tego nie potwierdza"}]},
                  "FaithfulnessScoreReason": {"reason": "scripted"}}
        return schema(**values[schema.__name__])

    async def a_generate(self, prompt, schema=None, **kwargs):
        return self.generate(prompt, schema, **kwargs)


CASE = LLMTestCase(input="Co mówi polityka podróży?",
                   actual_output="Wyjazdy zagraniczne wymagają zgody CFO. Limit za hotel to 500 PLN za noc.",
                   retrieval_context=["Wyjazdy zagraniczne wymagają zgody CFO."])


@pytest.mark.parametrize("second_verdict", ["borderline", "no"])
def test_an_unsupported_or_contradicted_claim_lowers_faithfulness(second_verdict):
    metric = make_metrics(ScriptedJudge(second_verdict))["faithfulness"]
    asyncio.run(metric.a_measure(CASE, _show_indicator=False))
    assert metric.score == 0.5, "liczy się tylko twierdzenie poparte kontekstem: 1 z 2"
    saved = evidence("faithfulness", metric)
    assert len(saved["claims"]) == 2 and [v["verdict"] for v in saved["verdicts"]] == ["yes", second_verdict]


def test_the_faithfulness_setting_is_explicit():
    assert METRIC_CONFIG["faithfulness"] == {"penalize_ambiguous_claims": True, "eval_mode": "llm"}
    metric = make_metrics(ScriptedJudge("borderline"))["faithfulness"]
    assert metric.penalize_ambiguous_claims is True


def test_the_examples_show_the_evidence_behind_a_low_score():
    row = {"id": "M01", "question": "Q?", "answer": "A.", "reference": "R.", "context_chunks": ["POL-001#ctx002"],
           "deepeval_faithfulness": 1.0, "deepeval_correctness": 0.8,
           "evidence": {"faithfulness": {"score": 1.0, "reason": "ok", "verdicts": []},
                        "correctness": {"score": 0.8, "reason": "dodaje szczegóły", "evaluation_steps": ["Porównaj fakty."]}}}
    text = format_examples({"rows": [row]})
    assert "ODPOWIEDŹ: A." in text and "WZORZEC:   R." in text and "POL-001#ctx002" in text
    assert "dodaje szczegóły" in text and "krok G-Eval 1 (wygenerowany dla tej odpowiedzi): Porównaj fakty." in text
