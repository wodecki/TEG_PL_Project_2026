"""Wczytuje i sprawdza config.yaml. Gotowy plik: nie edytujesz go."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


class ConfigError(RuntimeError):
    """Brakuje wymaganej wartości konfiguracji albo jest nieprawidłowa."""


class MissingConfigError(ConfigError):
    """Nie ustawiono wymaganej zmiennej środowiskowej (np. klucza API)."""


REQUIRED_KEYS = [
    "paths.corpus_dir",
    "paths.corpus_catalog",
    "paths.eval_queries",
    "paths.embedding_cache",
    "paths.mini_project_1_output_dir",
    "paths.mini_project_2_questions",
    "paths.mini_project_2_output_dir",
    "paths.mini_project_3_dialogues",
    "paths.mini_project_3_output_dir",
    "paths.company_data_dir",
    "paths.mini_project_4_questions",
    "paths.mini_project_4_output_dir",
    "paths.mini_project_5_conversations",
    "paths.mini_project_5_output_dir",
    "mcp.startup_timeout_s",
    "mcp.call_timeout_s",
    "mcp.cleanup_timeout_s",
    "agent.max_steps",
    "agent.timeout_s",
    "policy.version",
    "policy.bands",
    "policy.exceptions",
    "policy.margin_floor",
    "policy.floor_role",
    "corpus.required_metadata",
    "tokenizer.encoding",
    "chunking.chunk_size",
    "chunking.chunk_overlap",
    "chunking.separators",
    "embeddings.model",
    "embeddings.dimensions",
    "embeddings.batch_size",
    "retrieval.top_k",
    "reference_llm.provider",
    "reference_llm.model",
    "llm.provider",
    "llm.model",
    "llm.temperature",
    "llm.base_urls",
    "llm.api_key_env",
    "cost.reference_model",
    "cost.prices_per_1m_tokens",
    "cost.scenario.questions_per_day",
    "cost.scenario.working_days_per_month",
    "cost.scenario.output_tokens_per_answer",
    "prompts.system",
    "prompts.answer_system",
    "prompts.understand_system",
    "prompts.agent_system",
    "prompts.assistant_understand_system",
]


@dataclass(frozen=True)
class Config:
    """Wczytana konfiguracja. `root` to folder, w którym leży config.yaml."""

    root: Path
    raw: dict[str, Any]

    def get(self, dotted_key: str) -> Any:
        node: Any = self.raw
        for part in dotted_key.split("."):
            if not isinstance(node, dict) or part not in node:
                raise ConfigError(f"Brak wartości konfiguracji '{dotted_key}' w {self.root / 'config.yaml'}")
            node = node[part]
        return node

    def path(self, dotted_key: str) -> Path:
        """Ścieżka z konfiguracji, liczona względem folderu pliku config.yaml."""
        return (self.root / self.get(dotted_key)).resolve()


def _read_yaml(path: Path) -> dict:
    if not path.is_file():
        raise ConfigError(f"Nie znaleziono pliku konfiguracji: {path}")
    with path.open(encoding="utf-8") as fh:
        raw = yaml.safe_load(fh)
    if not isinstance(raw, dict):
        raise ConfigError(f"Plik konfiguracji {path} nie zawiera mapowania YAML (par klucz: wartość)")
    return raw


def _apply_override(base: dict, override: dict, where: str = "") -> None:
    """Zastępuje wartości w `base` wartościami z `override`; każdy klucz musi już istnieć w `base`."""
    for key, value in override.items():
        dotted = f"{where}{key}"
        if key not in base:
            raise ConfigError(f"Klucza '{dotted}' z pliku nadpisań nie ma w config.yaml (literówka?)")
        if isinstance(value, dict) and isinstance(base[key], dict):
            _apply_override(base[key], value, f"{dotted}.")
        else:
            base[key] = value


def load_config(config_path: Path, override_path: Path | None = None) -> Config:
    """Wczytuje config.yaml; `override_path` wskazuje plik YAML, którego wartości zastępują
    część wartości z config.yaml.

    Ścieżki są zawsze liczone względem folderu config.yaml, niezależnie od tego, gdzie leży
    plik nadpisań. Sam config.yaml nigdy się nie zmienia.
    """
    config_path = Path(config_path)
    raw = _read_yaml(config_path)
    if override_path is not None:
        _apply_override(raw, _read_yaml(Path(override_path)))
    config = Config(root=config_path.parent.resolve(), raw=raw)
    for key in REQUIRED_KEYS:
        config.get(key)
    return config
