"""Ocena końcowego asystenta tura po turze, według OCZEKIWANEJ trasy każdej tury. Gotowy plik: nie edytujesz go.

O tym, które sprawdzenia dotyczą tury, decyduje wyłącznie jej WZORZEC, zanim ktokolwiek spojrzy
na wynik (`applicable`). Działanie asystenta może skutkować negatywnym wynikiem sprawdzenia,
ale nigdy nie powoduje jego pominięcia:

  każda tura         route (rozpoznany rodzaj); status, fields (co LLM wyodrębnił, reguła z MP3:
                     liczby równe z dokładnością do 0,01), request, approvers, pauses: tam, gdzie
                     podaje je wzorzec; agent_trace (jeden w turze o dane, żadnego w pozostałych)
  document_question  ze wzorcem dla agenta: tool_coverage (jeśli wymienia needs), arguments_correct
  ze wzorcem agenta  (jeśli wymienia calculations), answer_facts (jeśli wymienia kluczowe fakty),
                     numbers_backed, no_approval_claim. Brak zapisu przebiegu lub pusty zapis albo
                     brak obliczenia tam, gdzie się go oczekuje, powoduje negatywny wynik tych sprawdzeń.
"""

from __future__ import annotations

from helpers.agent_trace import AgentGold, Need
from helpers.assistant import trace_from_record

DIMENSIONS = ["route", "status", "fields", "pauses", "approvers", "request", "agent_trace", "tool_coverage",
              "arguments_correct", "answer_facts", "numbers_backed", "no_approval_claim"]


def applicable(expect: dict) -> list[str]:
    """Sprawdzenia zdefiniowane przez wzorzec tej tury, w kolejności DIMENSIONS. Zależą tylko od wzorca."""
    dims = {"route", "agent_trace"} | {k for k in ("status", "fields", "pauses", "approvers", "request") if k in expect}
    agent = expect.get("agent") if expect["kind"] == "document_question" else None
    if agent is not None:
        dims |= {"numbers_backed", "no_approval_claim"}
        if agent.get("needs"):
            dims.add("tool_coverage")
        if agent.get("calculations"):
            dims.add("arguments_correct")
        if agent.get("key_facts"):
            dims.add("answer_facts")
    return [d for d in DIMENSIONS if d in dims]


def _same(a, b) -> bool:
    if isinstance(a, (int, float)) and isinstance(b, (int, float)) and not isinstance(a, bool) and not isinstance(b, bool):
        return abs(a - b) < 0.01
    return a == b


def _fields_match(expected: dict, actual: dict | None) -> bool:
    return actual is not None and all(_same(actual.get(k), v) for k, v in expected.items())


def score_assistant_turn(entry: dict, expect: dict, claim_phrases: list[str], score_trace) -> dict:
    """{wymiar: True / False} dla dokładnie tych wymiarów, które wymienia applicable(expect), oraz
    "agent_score" (słownik z MP4), gdy tura o dane ma zapis przebiegu. score_trace: krok 4 z MP4."""
    turn = entry.get("turn") or {}
    trace = trace_from_record(entry.get("record"))
    result: dict = {}
    for dim in applicable(expect):
        if dim == "route":
            result[dim] = turn.get("kind") == expect["kind"]
        elif dim == "status":
            result[dim] = entry.get("status") == expect["status"]
        elif dim == "fields":
            result[dim] = bool(turn) and _fields_match(expect["fields"], turn)
        elif dim == "request":
            result[dim] = _fields_match(expect["request"], entry.get("request"))
        elif dim == "approvers":
            result[dim] = entry.get("approvers") == expect["approvers"]
        elif dim == "pauses":
            result[dim] = [list(p) for p in entry.get("pauses", [])] == [list(p) for p in expect["pauses"]]
        elif dim == "agent_trace":
            result[dim] = (trace is not None) == (expect["kind"] == "document_question")
    agent = expect.get("agent") if expect["kind"] == "document_question" else None
    if agent is None:
        return result
    agent_dims = [d for d in applicable(expect) if d in ("tool_coverage", "arguments_correct", "answer_facts",
                                                         "numbers_backed", "no_approval_claim")]
    if trace is None:                  # brak zapisu przebiegu: brakuje całej oczekiwanej pracy agenta
        result.update({d: False for d in agent_dims})
        return result
    gold = AgentGold(id=entry.get("user", "")[:40], question=trace.question, kind="mp5",
                     needs=[Need(**n) for n in agent.get("needs", [])], calculations=agent.get("calculations", []),
                     key_facts=agent.get("key_facts", []), approval_claim_phrases=claim_phrases)
    score = score_trace(trace, gold)
    result["agent_score"] = score
    checks = {
        "tool_coverage": score["tool_coverage"] == 1,
        "arguments_correct": score["arguments_correct"] is True,   # None = brak obliczenia tam, gdzie się go oczekiwało
        "answer_facts": score["answer_fact_coverage"] == 1,
        "numbers_backed": bool(trace.answer) and not score["uncovered_numbers"],
        "no_approval_claim": bool(trace.answer) and not score["approval_claim"],
    }
    result.update({d: checks[d] for d in agent_dims})
    return result


def load_conversations(config) -> list[dict]:
    """Rozmowy z Miniprojektu 5, a po nich dialogi z Miniprojektu 3 z nałożonymi uzupełnieniami
    z MP5 (np. wzorcem agenta dla D7). Pliki są tylko czytane, nigdy zmieniane."""
    import copy

    import yaml

    mp5 = yaml.safe_load(config.path("paths.mini_project_5_conversations").read_text(encoding="utf-8"))
    mp3 = yaml.safe_load(config.path("paths.mini_project_3_dialogues").read_text(encoding="utf-8"))["dialogues"]
    dialogues = copy.deepcopy(mp3)
    for dialogue in dialogues:
        for number, extra in (mp5.get("mp3_overlays", {}).get(dialogue["id"]) or {}).items():
            dialogue["turns"][int(number) - 1]["expect"].update(copy.deepcopy(extra))
    return mp5["conversations"] + dialogues


def summarise(scores: list[dict]) -> dict:
    """{wymiar: (zaliczone, ocenione)} po turach, które go definiują."""
    return {dim: (sum(s[dim] is True for s in scores if dim in s), sum(1 for s in scores if dim in s))
            for dim in DIMENSIONS}
