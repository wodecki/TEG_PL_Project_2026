"""Sprawdza gotową uwagę o LLM-ach innych niż referencyjny (helpers/llm_notice.py). Tu nic nie piszesz."""

from helpers.llm_notice import other_llm_note
from mini_project_1.tests.conftest import config_with_llm


def test_no_note_for_the_reference_llm(config):
    reference = config.get("reference_llm")
    assert other_llm_note(config_with_llm(config, provider=reference["provider"], model=reference["model"])) is None


def test_note_names_both_llms_for_another_llm(config):
    note = other_llm_note(config_with_llm(config, provider="ollama", model="gemma3:4b"))
    assert note and "ollama / gemma3:4b" in note and config.get("reference_llm.model") in note
