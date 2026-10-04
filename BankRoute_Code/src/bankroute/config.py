"""Central configuration and stable project paths.

Secrets are read at runtime only.  The OpenRouter key is never persisted or
included in API responses; callers can inspect only the boolean availability.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
ARTIFACT_DIR = PROJECT_ROOT / "artifacts"
EVAL_DIR = PROJECT_ROOT / "evals"
LOG_DIR = PROJECT_ROOT / "logs"

DEFAULT_OPENROUTER_MODEL = "openai/gpt-4o-mini"
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
MAX_MESSAGE_CHARS = 500
MIN_MESSAGE_CHARS = 3


def openrouter_key_available() -> bool:
    """Return key availability without exposing the secret value."""

    return bool(os.getenv("OPENROUTER_API_KEY", "").strip())


def openrouter_model() -> str:
    return os.getenv("OPENROUTER_MODEL", DEFAULT_OPENROUTER_MODEL).strip()


def load_thresholds() -> Dict[str, Any]:
    """Load thresholds selected on validation data, with safe defaults."""

    path = ARTIFACT_DIR / "thresholds.json"
    defaults: Dict[str, Any] = {
        "scope_threshold": 0.60,
        "intent_confidence_threshold": 0.58,
        "intent_margin_threshold": 0.10,
        "llm_agreement_threshold": 0.75,
    }
    if not path.exists():
        return defaults
    values = json.loads(path.read_text(encoding="utf-8"))
    defaults.update(values)
    return defaults

