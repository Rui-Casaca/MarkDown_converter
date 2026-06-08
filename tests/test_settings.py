"""Tests for the persistent settings store."""

from __future__ import annotations

from pathlib import Path

import doc2md.settings as settings


class TestLoadLanguage:
    def test_returns_default_when_missing(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.setattr(settings, "SETTINGS_PATH", tmp_path / "missing.json")
        assert settings.load_language("en") == "en"

    def test_reads_saved_language(self, tmp_path: Path, monkeypatch) -> None:
        path = tmp_path / "settings.json"
        path.write_text('{"language": "pt"}', encoding="utf-8")
        monkeypatch.setattr(settings, "SETTINGS_PATH", path)
        assert settings.load_language("en") == "pt"

    def test_invalid_json_returns_default(self, tmp_path: Path, monkeypatch) -> None:
        path = tmp_path / "settings.json"
        path.write_text("not json", encoding="utf-8")
        monkeypatch.setattr(settings, "SETTINGS_PATH", path)
        assert settings.load_language("en") == "en"

    def test_non_string_language_returns_default(self, tmp_path: Path, monkeypatch) -> None:
        path = tmp_path / "settings.json"
        path.write_text('{"language": 123}', encoding="utf-8")
        monkeypatch.setattr(settings, "SETTINGS_PATH", path)
        assert settings.load_language("en") == "en"


class TestSaveLanguage:
    def test_writes_and_reads_back(self, tmp_path: Path, monkeypatch) -> None:
        path = tmp_path / "settings.json"
        monkeypatch.setattr(settings, "SETTINGS_PATH", path)
        settings.save_language("pt")
        assert path.exists()
        assert settings.load_language("en") == "pt"

    def test_preserves_other_keys(self, tmp_path: Path, monkeypatch) -> None:
        path = tmp_path / "settings.json"
        path.write_text('{"other": "value"}', encoding="utf-8")
        monkeypatch.setattr(settings, "SETTINGS_PATH", path)
        settings.save_language("pt")

        import json

        data = json.loads(path.read_text(encoding="utf-8"))
        assert data["other"] == "value"
        assert data["language"] == "pt"

    def test_save_failure_is_silent(self, tmp_path: Path, monkeypatch) -> None:
        # Point at a path whose parent does not exist and cannot be written.
        monkeypatch.setattr(settings, "SETTINGS_PATH", tmp_path / "nope" / "deep" / "s.json")
        # Should not raise even though the write fails.
        settings.save_language("pt")
