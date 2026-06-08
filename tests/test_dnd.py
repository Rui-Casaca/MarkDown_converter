"""Tests for the optional drag-and-drop helpers.

These tests avoid importing tkinter or tkinterdnd2 so they stay safe to run in a
headless CI environment. They exercise the graceful-degradation paths and the
drop-payload parser using lightweight fakes.
"""

from __future__ import annotations

from doc2md.ui.dnd import enable_drag_and_drop, parse_drop_data, register_drop_target


class _FakeTk:
    @staticmethod
    def splitlist(data: str) -> tuple[str, ...]:
        # Mimic Tcl's splitlist for brace-wrapped, space-separated paths.
        parts: list[str] = []
        token = ""
        in_brace = False
        for char in data:
            if char == "{":
                in_brace = True
            elif char == "}":
                in_brace = False
            elif char == " " and not in_brace:
                if token:
                    parts.append(token)
                    token = ""
            else:
                token += char
        if token:
            parts.append(token)
        return tuple(parts)


class _FakeWidget:
    def __init__(self) -> None:
        self.tk = _FakeTk()


class TestGracefulDegradation:
    def test_enable_returns_false_without_library(self) -> None:
        assert enable_drag_and_drop(object()) is False

    def test_register_returns_false_without_library(self) -> None:
        assert register_drop_target(object(), lambda paths: None) is False


class TestParseDropData:
    def test_empty_returns_empty_list(self) -> None:
        assert parse_drop_data(_FakeWidget(), "") == []

    def test_splits_space_separated_paths(self) -> None:
        result = parse_drop_data(_FakeWidget(), "C:/a.pdf C:/b.docx")
        assert result == ["C:/a.pdf", "C:/b.docx"]

    def test_handles_braced_paths_with_spaces(self) -> None:
        result = parse_drop_data(_FakeWidget(), "{C:/a b/x.pdf} C:/y.docx")
        assert result == ["C:/a b/x.pdf", "C:/y.docx"]

    def test_fallback_when_splitlist_fails(self) -> None:
        class _Broken:
            class tk:  # noqa: N801 - mimic widget.tk namespace
                @staticmethod
                def splitlist(data: str):
                    raise RuntimeError("boom")

        assert parse_drop_data(_Broken(), "single.pdf") == ["single.pdf"]
