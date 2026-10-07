"""Sprawdza gotowy program answer_questions.py (bez LLM-a: z atrapą). Tu nic nie piszesz."""

import json

import pytest
from langchain_core.runnables import RunnableLambda

import mini_project_2.src.answer_questions as program
from helpers.records import Answer, Verdict, load_run


class FakeBySchema:
    """Odpowiada na każde pytanie albo każde wywołanie kończy błędem."""

    def __init__(self, fail: bool = False):
        self.fail = fail

    def with_structured_output(self, schema, **kwargs):
        def respond(prompt):
            if self.fail:
                raise ValueError("sztuczny błąd schematu")
            if schema is Answer:
                return Answer(answer="CFO.", citations=["POL-001"], answerable=True)
            return Verdict(correct=True, grounded=True, reason="atrapa")
        return RunnableLambda(respond)


def run(monkeypatch, tmp_path, llm):
    override = tmp_path / "override.yaml"
    override.write_text(f"paths:\n  mini_project_2_output_dir: {tmp_path / 'out'}\n", encoding="utf-8")
    monkeypatch.setattr(program, "build_llm", lambda config: llm)
    monkeypatch.setattr("sys.argv", ["answer_questions.py", "--config-override", str(override)])
    program.main()
    out = tmp_path / "out"
    return load_run(out / "answers.json"), json.loads((out / "live_report.json").read_text(encoding="utf-8"))


def test_a_failed_run_replaces_the_previous_one(monkeypatch, tmp_path):
    (first_run, _), first_report = run(monkeypatch, tmp_path, FakeBySchema())
    assert first_report["summary"]["errors"] == 0
    with pytest.raises(SystemExit):
        run(monkeypatch, tmp_path, FakeBySchema(fail=True))
    run_info, records = load_run(tmp_path / "out" / "answers.json")
    report = json.loads((tmp_path / "out" / "live_report.json").read_text(encoding="utf-8"))
    assert report["summary"]["errors"] == len(records) == 12, "nieudany przebieg musi zostać zapisany, a nie stary zachowany"
    assert report["run_id"] == run_info["run_id"], "oba pliki należą do tego samego przebiegu"
    assert report["run_id"] != first_report["run_id"], "dwa przebiegi, nawet w tej samej sekundzie, dostają różne id"


def test_an_all_error_first_run_is_saved(monkeypatch, tmp_path):
    with pytest.raises(SystemExit):
        run(monkeypatch, tmp_path, FakeBySchema(fail=True))
    _, records = load_run(tmp_path / "out" / "answers.json")
    assert all(row["record"].error for row in records)



def test_the_deepeval_table_counts_missing_scores():
    from mini_project_2.src.compare_with_deepeval import format_table
    rows = [{"id": "M01", "key_fact_coverage": 1.0, "judge_correct": True, "judge_grounded": True,
             "deepeval_faithfulness": 1.0, "deepeval_correctness": 0.8, "reasons": {}},
            {"id": "M02", "key_fact_coverage": 1.0, "judge_correct": True, "judge_grounded": True,
             "deepeval_faithfulness": None, "deepeval_correctness": 1.0, "reasons": {}}]
    table = format_table({"run_id": "r", "answered_by": "x", "model": "m", "deepeval_version": "4.2.8",
                          "judge_cost_usd": 0.044, "rows": rows})
    assert "M01" in table and "0.80" in table and "DeepEval: 1 z 2" in table and "0,044 USD" in table


def test_without_deepeval_the_program_says_how_to_install(monkeypatch, tmp_path):
    import builtins
    import pytest
    from mini_project_2.src import compare_with_deepeval as program
    real_import = builtins.__import__

    def no_deepeval(name, *args, **kwargs):
        if name.startswith("deepeval"):
            raise ModuleNotFoundError("No module named 'deepeval'")
        return real_import(name, *args, **kwargs)
    monkeypatch.setattr(builtins, "__import__", no_deepeval)
    (tmp_path / "answers.json").write_text("{}")
    (tmp_path / "live_report.json").write_text("{}")
    monkeypatch.setattr(program, "load_config", lambda path: type("C", (), {"path": lambda self, key: tmp_path})())
    with pytest.raises(SystemExit, match="uv sync --extra deepeval"):
        program.main()
