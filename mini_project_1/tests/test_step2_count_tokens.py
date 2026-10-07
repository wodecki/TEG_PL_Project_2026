import pytest

from mini_project_1.src.step2_count_tokens import count_tokens, monthly_cost


@pytest.mark.parametrize(
    "text, expected",
    [
        ("", 0),
        ("Hello, world!", 4),                   # angielski tekst celowo: dla porównania z polskim poniżej
        ("Kovalo Distribution", 3),
        ("OTIF = zamówienia dostarczone na czas i w komplecie / wszystkie dostarczone zamówienia", 25),
    ],
)
def test_count_tokens(config, text, expected):
    got = count_tokens(text, config)
    assert got == expected, f"count_tokens({text!r}) powinno zwrócić {expected}, otrzymano {got}"


def test_count_tokens_uses_the_tokenizer_from_config(config):
    import copy

    from helpers.config import Config

    raw = copy.deepcopy(config.raw)
    raw["tokenizer"]["encoding"] = "cl100k_base"  # starszy tokenizer: inna liczba tokenów
    assert count_tokens("Kovalo Distribution", Config(root=config.root, raw=raw)) == 4, \
        "count_tokens musi brać nazwę tokenizera z config.get('tokenizer.encoding')"


def test_monthly_cost_example_from_the_step_description(config):
    got = monthly_cost(1000, config)
    assert got == pytest.approx(19.53), f"monthly_cost(1000, config) powinno zwrócić 19.53 USD, otrzymano {got}"


def test_monthly_cost_grows_with_input_tokens(config):
    assert monthly_cost(2000, config) > monthly_cost(1000, config) > monthly_cost(0, config) > 0, \
        "więcej tokenów wejściowych musi kosztować więcej; nawet 0 tokenów wejściowych coś kosztuje (odpowiedź)"


def test_monthly_cost_uses_the_reference_model_not_your_llm(config):
    from mini_project_1.tests.conftest import config_with_llm

    mine = config_with_llm(config, provider="ollama", model="gemma3:4b")
    assert monthly_cost(1000, mine) == pytest.approx(monthly_cost(1000, config)), \
        "monthly_cost musi liczyć cenę dla config.get('cost.reference_model'), niezależnie od używanego LLM-a (llm.model)"
