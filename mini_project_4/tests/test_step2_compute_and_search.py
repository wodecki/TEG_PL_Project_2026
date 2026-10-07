"""Testy kroku 2: dokładna arytmetyka kary, sprawdzenie polityki tylko do odczytu, surowe fragmenty."""

import math

import pytest

from mini_project_4.src.step2_compute_and_search import calculate_otif_penalty, check_discount_policy, search_documents


def penalty(otif, invoice=18240000, target=97, rate=2, cap=10):
    return calculate_otif_penalty(otif_pct=otif, target_pct=target, rate_per_full_point_pct=rate, cap_pct=cap,
                                  invoice_grosze=invoice)


def test_july_with_every_intermediate_value():
    result = penalty(94.6)
    assert result.status == "ok"
    assert result.shortfall_points == 2.4, "97 - 94.6 to dokładnie 2.4 punktu (na floatach: 2.4000000000000057): użyj Decimal(str(x))"
    assert result.full_points == 2
    assert (result.penalty_pct_uncapped, result.penalty_pct) == (4, 4)
    assert result.penalty_grosze == 729600, "4% z 18 240 000 groszy"
    assert result.currency == "PLN"
    assert (result.otif_pct, result.target_pct, result.rate_per_full_point_pct, result.cap_pct, result.invoice_grosze) == \
        (94.6, 97, 2, 10, 18240000), "powtórz dane wejściowe"


@pytest.mark.parametrize("otif, full_points, grosze", [
    (95.2, 1, 364800),      # brakuje 1,8: 1 pełny punkt, 2% z 18 240 000 groszy
    (96.4, 0, 0),           # maj: brakuje 0,6
    (96.01, 0, 0),          # brakuje 0,99: to nie pełny punkt
    (96.0, 1, 364800),      # dokładnie 1 punkt
    (97.0, 0, 0),           # równo z celem
    (98.5, 0, 0),           # powyżej celu: brak nigdy nie jest ujemny
])
def test_full_points_are_whole_points(otif, full_points, grosze):
    result = penalty(otif)
    assert result.full_points == full_points, f"OTIF {otif}% vs 97%"
    assert result.penalty_grosze == grosze
    assert result.shortfall_points >= 0


def test_a_full_point_floats_would_lose():
    # na floatach 64.1 - 63.1 = 0.9999999999999929, a część całkowita to 0: Decimal daje dokładnie 1.0
    result = penalty(63.1, invoice=10000, target=64.1)
    assert (result.shortfall_points, result.full_points, result.penalty_grosze) == (1.0, 1, 200)


def test_exact_values_without_float_noise():
    # na floatach 96 - 95.1 = 0.9000000000000057: rekord musi podać 0.9
    result = penalty(95.1, target=96)
    assert result.shortfall_points == 0.9 and result.full_points == 0


def test_the_cap():
    result = penalty(85.0)                      # 12 pełnych punktów -> 24%, limit 10%
    assert (result.full_points, result.penalty_pct_uncapped, result.penalty_pct) == (12, 24, 10)
    assert result.penalty_grosze == 1824000


@pytest.mark.parametrize("invoice, grosze", [(125, 3), (124, 2), (175, 4), (25, 1)])
def test_rounding_half_up_to_whole_grosze(invoice, grosze):
    # 1 pełny punkt x 2%: 125 groszy -> 2.5 -> 3 (round(2.5) w Pythonie daje 2: zaokrągla połówki do parzystej);
    # 124 -> 2.48 -> 2; 175 -> 3.5 -> 4; 25 -> 0.5 -> 1
    assert penalty(96.0, invoice=invoice).penalty_grosze == grosze


@pytest.mark.parametrize("change", [
    {"otif_pct": float("nan")}, {"otif_pct": 101}, {"target_pct": -1}, {"rate_per_full_point_pct": -2},
    {"cap_pct": 120}, {"invoice_grosze": 100.5}, {"invoice_grosze": -1}, {"otif_pct": None}, {"otif_pct": True},
])
def test_invalid_inputs(change):
    args = dict(otif_pct=94.6, target_pct=97, rate_per_full_point_pct=2, cap_pct=10, invoice_grosze=18240000)
    args.update(change)
    result = calculate_otif_penalty(**args)
    assert result.status == "invalid_request", f"{change} musi zostać odrzucone"
    assert result.penalty_grosze is None and result.message



@pytest.mark.parametrize("name, value", [("otif_pct", 101), ("target_pct", -1), ("rate_per_full_point_pct", -2),
                                         ("cap_pct", 120)])
def test_a_message_does_not_depend_on_int_or_float(name, value):
    args = dict(otif_pct=94.6, target_pct=97, rate_per_full_point_pct=2, cap_pct=10, invoice_grosze=18240000)
    as_int = calculate_otif_penalty(**{**args, name: value})
    as_float = calculate_otif_penalty(**{**args, name: float(value)})
    assert as_int.message == as_float.message, (
        f"{name}={value} i {float(value)} muszą dać ten sam komunikat, a dały {as_int.message!r} i {as_float.message!r}: "
        "klient MCP może wysłać każdą z tych form (Miniprojekt 5 porównuje wyniki twoich narzędzi wywołanych bezpośrednio i przez MCP)")

def test_policy_check_reuses_the_rules_engine(config):
    result = check_discount_policy(config, discount_pct=22, margin_after_pct=7, strategic_account=True)
    assert result.status == "ok"
    assert result.approvers == ["Dyrektor handlowy", "CFO"]
    assert result.version == "course-v1" and result.margin_checked is True and result.partial is False
    assert result.reasons
    assert "niczego nie zatwierdza" in result.note


def test_an_unknown_margin_is_a_partial_check(config):
    result = check_discount_policy(config, discount_pct=14)
    assert result.approvers == ["Dyrektor handlowy"]
    assert result.margin_checked is False and result.partial is True


def test_volume_rebates_are_out_of_scope(config):
    result = check_discount_policy(config, discount_pct=4, contractual_volume_rebate=True)
    assert result.status == "out_of_scope" and result.approvers == []
    assert "warunków kredytowych i handlowych" in result.message


def test_invalid_policy_input(config):
    result = check_discount_policy(config, discount_pct=140)
    assert result.status == "invalid_request" and result.approvers == [] and "discount" in result.message


def test_search_returns_raw_passages_with_ids(store):
    result = search_documents(store, "TransBałt terminowe dostawy palet", 2)
    assert result.status == "ok" and result.query == "TransBałt terminowe dostawy palet"
    assert len(result.passages) == 2 and store.ks == [2]
    for passage in result.passages:
        assert passage.doc_id and passage.chunk_id.startswith(passage.doc_id) and passage.text


def test_an_empty_question(store):
    assert search_documents(store, "  ", 3).status == "invalid_request"
