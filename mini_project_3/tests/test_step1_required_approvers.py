import math

import pytest

from helpers.workflow import DiscountRequest
from mini_project_3.src.step1_required_approvers import required_approvers
from mini_project_3.tests.conftest import config_with_policy

R = DiscountRequest

# Sprawdzone ręcznie według kursowej interpretacji course-v1 (README, „Polityka rabatowa jako kod”).
CASES = [
    (R(discount_pct=5, margin_after_pct=10), ["Przedstawiciel handlowy"]),
    (R(discount_pct=5.01, margin_after_pct=10), ["Regionalny kierownik sprzedaży"]),
    (R(discount_pct=12, margin_after_pct=10), ["Regionalny kierownik sprzedaży"]),
    (R(discount_pct=12.01, margin_after_pct=10), ["Dyrektor handlowy"]),
    (R(discount_pct=20, margin_after_pct=10), ["Dyrektor handlowy"]),
    (R(discount_pct=20.01, margin_after_pct=10), ["CEO", "CFO"]),
    (R(discount_pct=8, margin_after_pct=9), ["Regionalny kierownik sprzedaży"]),
    (R(discount_pct=8, margin_after_pct=8.99), ["Regionalny kierownik sprzedaży", "CFO"]),
    (R(discount_pct=3, margin_after_pct=7), ["Przedstawiciel handlowy", "CFO"]),
    (R(discount_pct=15, competitor_offer=True, margin_after_pct=10), ["Regionalny kierownik sprzedaży"]),
    (R(discount_pct=15.01, competitor_offer=True, margin_after_pct=10), ["Dyrektor handlowy"]),
    (R(discount_pct=25, strategic_account=True, margin_after_pct=10), ["Dyrektor handlowy"]),
    (R(discount_pct=25.01, strategic_account=True, margin_after_pct=10), ["CEO", "CFO"]),
    (R(discount_pct=35, clearance=True, margin_after_pct=4), ["Regionalny kierownik sprzedaży"]),
    (R(discount_pct=35.01, clearance=True, margin_after_pct=10), ["CEO", "CFO"]),
    (R(discount_pct=3, strategic_account=True, margin_after_pct=10), ["Przedstawiciel handlowy"]),
    (R(discount_pct=22, margin_after_pct=10), ["CEO", "CFO"]),
    (R(discount_pct=22, strategic_account=True, margin_after_pct=7), ["Dyrektor handlowy", "CFO"]),
    (R(discount_pct=14, strategic_account=True, competitor_offer=True, margin_after_pct=7), ["Regionalny kierownik sprzedaży", "CFO"]),
    (R(discount_pct=30, clearance=True, margin_after_pct=4), ["Regionalny kierownik sprzedaży"]),
    (R(discount_pct=36, clearance=True, margin_after_pct=4), ["CEO", "CFO"]),
    (R(discount_pct=25, margin_after_pct=5), ["CEO", "CFO"]),
]


@pytest.mark.parametrize("request_, expected", CASES, ids=[f"{c[0].discount_pct}%-{i}" for i, c in enumerate(CASES)])
def test_hand_checked_cases(request_, expected, config):
    decision = required_approvers(request_, config)
    assert decision.approvers == expected, f"{request_.model_dump()} -> oczekiwano {expected}, jest {decision.approvers}"


def test_decision_carries_reasons_and_version(config):
    decision = required_approvers(R(discount_pct=22, strategic_account=True, margin_after_pct=7), config)
    assert decision.version == config.get("policy.version")
    assert len(decision.reasons) >= 3, "jedno uzasadnienie na każdą regułę, która wpłynęła na wynik (przedział, wyjątek, minimalna marża)"
    assert decision.margin_checked is True


def test_missing_margin_means_floor_not_checked(config):
    decision = required_approvers(R(discount_pct=8), config)
    assert decision.approvers == ["Regionalny kierownik sprzedaży"] and decision.margin_checked is False


@pytest.mark.parametrize("bad", [R(discount_pct=None), R(discount_pct=math.nan), R(discount_pct=101), R(discount_pct=-1),
                                 R(discount_pct=10, margin_after_pct=150), R(discount_pct=10, margin_after_pct=math.inf)])
def test_invalid_input_raises(bad, config):
    with pytest.raises(ValueError):
        required_approvers(bad, config)


def test_numbers_come_from_config(config):
    stricter = config_with_policy(config, margin_floor=10)
    assert required_approvers(R(discount_pct=8, margin_after_pct=9.5), stricter).approvers == ["Regionalny kierownik sprzedaży", "CFO"], \
        "czytaj margin_floor (a także przedziały i wyjątki) z config.get('policy')"
