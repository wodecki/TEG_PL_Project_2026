"""Sprawdza gotowy loader konfiguracji (helpers/config.py). Tu nic nie piszesz."""

import hashlib

import pytest

from helpers.config import ConfigError, load_config
from mini_project_1.tests.conftest import ROOT


def test_override_changes_only_the_given_values(tmp_path):
    canonical = ROOT / "config.yaml"
    before = hashlib.sha256(canonical.read_bytes()).hexdigest()
    override = tmp_path / "elsewhere" / "ollama.yaml"
    override.parent.mkdir()
    override.write_text("llm:\n  provider: ollama\n  model: gemma3:4b\n", encoding="utf-8")

    base, changed = load_config(canonical), load_config(canonical, override)

    assert (changed.get("llm.provider"), changed.get("llm.model")) == ("ollama", "gemma3:4b")
    assert changed.get("llm.base_urls") == base.get("llm.base_urls"), "wartości, których nie ma w pliku nadpisującym, pozostają bez zmian"
    assert changed.path("paths.corpus_dir") == base.path("paths.corpus_dir"), \
        "ścieżki do danych muszą się rozwijać względem projektu, a nie folderu pliku nadpisującego"
    assert hashlib.sha256(canonical.read_bytes()).hexdigest() == before, "sam config.yaml nie może się zmienić"


def test_override_with_an_unknown_key_fails(tmp_path):
    override = tmp_path / "typo.yaml"
    override.write_text("llm:\n  modle: gemma3:4b\n", encoding="utf-8")
    with pytest.raises(ConfigError, match="llm.modle"):
        load_config(ROOT / "config.yaml", override)
