import pytest
from langchain_core.language_models.fake_chat_models import FakeMessagesListChatModel
from langchain_core.messages import AIMessage
from langchain_ollama import ChatOllama
from langchain_openai import ChatOpenAI

from helpers.config import ConfigError, MissingConfigError
from mini_project_1.src.step6_connect_llm import build_llm, measure_call
from mini_project_1.tests.conftest import config_with_llm

# Sztuczne klucze: testy tylko budują modele, nigdy ich nie wywołują.


@pytest.fixture
def no_keys(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    return monkeypatch


def test_openai(config, no_keys):
    no_keys.setenv("OPENAI_API_KEY", "sk-test-openai")
    llm = build_llm(config_with_llm(config, provider="openai", model="gpt-test", temperature=0.3))
    assert isinstance(llm, ChatOpenAI), f"dostawca openai musi dać model czatu OpenAI, otrzymano {type(llm).__name__}"
    assert llm.model_name == "gpt-test", "model musi pochodzić z config.get('llm.model')"
    assert llm.temperature == 0.3, "temperatura musi pochodzić z config.get('llm.temperature')"
    assert llm.openai_api_key.get_secret_value() == "sk-test-openai"


def test_openrouter(config, no_keys):
    no_keys.setenv("OPENROUTER_API_KEY", "sk-test-openrouter")
    cfg = config_with_llm(config, provider="openrouter", model="vendor/model-test")
    llm = build_llm(cfg)
    assert isinstance(llm, ChatOpenAI), \
        f"OpenRouter udostępnia interfejs zgodny z API OpenAI: użyj klasy modelu czatu OpenAI, otrzymano {type(llm).__name__}"
    assert llm.model_name == "vendor/model-test"
    assert llm.openai_api_base == cfg.get("llm.base_urls")["openrouter"], \
        "skieruj model na config.get('llm.base_urls')['openrouter']"
    assert llm.openai_api_key.get_secret_value() == "sk-test-openrouter", \
        "klucz musi pochodzić z OPENROUTER_API_KEY, a nie z OPENAI_API_KEY"


def test_ollama_needs_no_key(config, no_keys):
    cfg = config_with_llm(config, provider="ollama", model="model-test", temperature=0)
    llm = build_llm(cfg)
    assert isinstance(llm, ChatOllama), f"dostawca ollama musi dać model czatu Ollama, otrzymano {type(llm).__name__}"
    assert llm.model == "model-test"
    assert llm.base_url == cfg.get("llm.base_urls")["ollama"], "użyj config.get('llm.base_urls')['ollama']"
    assert llm.temperature == 0


@pytest.mark.parametrize("provider, variable", [("openai", "OPENAI_API_KEY"), ("openrouter", "OPENROUTER_API_KEY")])
def test_missing_key_names_the_variable(config, no_keys, provider, variable):
    with pytest.raises(MissingConfigError, match=variable):
        build_llm(config_with_llm(config, provider=provider))


def test_unknown_provider(config, no_keys):
    with pytest.raises(ConfigError, match="ollama"):
        build_llm(config_with_llm(config, provider="carrier-pigeon"))


def test_measure_call_reports_the_provider_token_counts():
    usage = {"input_tokens": 12, "output_tokens": 3, "total_tokens": 15}
    llm = FakeMessagesListChatModel(responses=[AIMessage(content="Dyrektor handlowy.", usage_metadata=usage)])
    got = measure_call(llm, "Kto zatwierdza rabat 15%?")
    assert got == {"answer": "Dyrektor handlowy.", "input_tokens": 12, "output_tokens": 3}


def test_measure_call_never_guesses_token_counts():
    llm = FakeMessagesListChatModel(responses=[AIMessage(content="Brak danych o zużyciu tokenów.")])
    with pytest.raises(ValueError):
        measure_call(llm, "Kto zatwierdza rabat 15%?")
