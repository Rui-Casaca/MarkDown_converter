"""Small persistent settings store for doc2md (currently the UI language)."""

from __future__ import annotations

import json
from pathlib import Path

SETTINGS_PATH = Path.home() / ".doc2md.json"


def load_language(default: str = "en") -> str:
    """Read the saved UI language, returning ``default`` when unavailable."""
    try:
        data = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
        language = data.get("language")
        if isinstance(language, str) and language:
            return language
    except Exception:
        pass
    return default


def save_language(language: str) -> None:
    """Persist the chosen UI language, ignoring any I/O errors."""
    try:
        data: dict[str, object] = {}
        if SETTINGS_PATH.exists():
            try:
                data = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
            except Exception:
                data = {}
        data["language"] = language
        SETTINGS_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")
    except Exception:
        pass
