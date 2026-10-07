import pytest

from mini_project_3.src.step5_score_transcript import score_transcript


def entry(kind="approval_request", request=None, approvers=None, pauses=(), status="approved", **turn_fields):
    return {"user": "u", "turn": {"kind": kind, **turn_fields}, "request": request, "approvers": approvers,
            "pauses": [list(p) for p in pauses], "status": status}


def test_each_stage_is_scored_separately():
    turns = [entry(request={"revision": 1, "discount_pct": 14.0}, approvers=["Dyrektor handlowy"],
                   pauses=[["approval", "Dyrektor handlowy"]], discount_pct=14.0),
             entry(kind="policy_question", approvers=["CEO", "CFO"], status="answered", discount_pct=22.0)]
    gold = [{"kind": "approval_request", "fields": {"discount_pct": 14}, "request": {"revision": 1, "discount_pct": 14},
             "approvers": ["Dyrektor handlowy"], "pauses": [["approval", "Dyrektor handlowy"]], "status": "approved"},
            {"kind": "approval_request", "fields": {"discount_pct": 22.004}, "approvers": ["CEO", "CFO"], "pauses": [],
             "status": "answered"}]
    s = score_transcript(turns, gold)
    assert s["route"] == [1, 2], "druga tura trafiła do pytań o politykę zamiast do wniosków o akceptację"
    assert s["fields"] == [2, 2], "22.0 i 22.004 są równe (różnica < 0.01)"
    assert s["request"] == [1, 1], "ocenia się tylko tury, których wzorzec zawiera 'request'"
    assert s["approvers"] == [2, 2] and s["pauses"] == [2, 2] and s["status"] == [2, 2]
    assert s["details"][1]["wrong"] == ["route"]


def test_failures_stay_in_the_denominators():
    turns = [entry(kind="error", request=None, approvers=None, pauses=(), status="error")]
    gold = [{"kind": "approval_request", "request": {"revision": 1}, "approvers": ["CFO"], "pauses": [["approval", "CFO"]],
             "status": "approved"}]
    s = score_transcript(turns, gold)
    assert s["route"] == [0, 1] and s["request"] == [0, 1] and s["approvers"] == [0, 1]
    assert s["errors"] == 1


def test_lengths_must_match():
    with pytest.raises(ValueError):
        score_transcript([entry()], [])
