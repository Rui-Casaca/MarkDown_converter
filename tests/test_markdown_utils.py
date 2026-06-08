"""Unit tests for :mod:`doc2md.markdown_utils`."""

from __future__ import annotations

from datetime import datetime

import pytest

from doc2md.markdown_utils import MarkdownUtils
from doc2md.models import ConversionOptions


class TestNormalizeText:
    def test_collapses_whitespace_and_tabs(self) -> None:
        assert MarkdownUtils.normalize_text("Hello   world\tx") == "Hello world x"

    def test_normalizes_line_endings(self) -> None:
        assert MarkdownUtils.normalize_text("line1\r\nline2\rline3") == "line1\nline2\nline3"

    def test_dehyphenates_across_line_break(self) -> None:
        assert MarkdownUtils.normalize_text("co-\noperate") == "cooperate"

    def test_strips_each_line(self) -> None:
        assert MarkdownUtils.normalize_text("  a  \n  b  ") == "a\nb"


class TestRemoveRepeatedEmptyLines:
    def test_collapses_and_trims(self) -> None:
        assert MarkdownUtils.remove_repeated_empty_lines(["", "a", "", "", "b", ""]) == ["a", "", "b"]

    def test_all_empty_returns_empty_list(self) -> None:
        assert MarkdownUtils.remove_repeated_empty_lines(["", "  ", ""]) == []

    def test_no_empties_unchanged(self) -> None:
        assert MarkdownUtils.remove_repeated_empty_lines(["a", "b"]) == ["a", "b"]


class TestLooksLikeHeading:
    @pytest.mark.parametrize(
        "line",
        [
            "INTRODUCTION",
            "Chapter 1",
            "1. Introduction",
            "The Quick Brown Fox",
            "1.2 Methods",
        ],
    )
    def test_positive_cases(self, line: str) -> None:
        assert MarkdownUtils.looks_like_heading(line) is True

    @pytest.mark.parametrize(
        "line",
        [
            "",
            "Introduction",
            "hello world",
            "This is a sentence.",
            "x" * 100,
        ],
    )
    def test_negative_cases(self, line: str) -> None:
        assert MarkdownUtils.looks_like_heading(line) is False


class TestGuessHeadingLevel:
    @pytest.mark.parametrize(
        ("line", "expected"),
        [
            ("1 Title", 3),
            ("1.2 Title", 4),
            ("1.2.3 Title", 5),
            ("1.2.3.4.5 Title", 6),
            ("Title", 3),
        ],
    )
    def test_levels(self, line: str, expected: int) -> None:
        assert MarkdownUtils.guess_heading_level(line) == expected


class TestConvertLineToMarkdown:
    def test_detects_heading_when_enabled(self) -> None:
        options = ConversionOptions(detect_headings=True)
        result = MarkdownUtils.convert_line_to_markdown("The Quick Brown Fox", options)
        assert result == "### The Quick Brown Fox"

    def test_no_heading_when_disabled(self) -> None:
        options = ConversionOptions(detect_headings=False)
        result = MarkdownUtils.convert_line_to_markdown("The Quick Brown Fox", options)
        assert result == "The Quick Brown Fox"

    def test_bullet_normalization(self) -> None:
        options = ConversionOptions(detect_headings=False)
        assert MarkdownUtils.convert_line_to_markdown("\u2022 item", options) == "- item"

    def test_dash_bullet_normalization(self) -> None:
        options = ConversionOptions(detect_headings=False)
        assert MarkdownUtils.convert_line_to_markdown("\u2013 item", options) == "- item"

    def test_empty_line_returns_empty(self) -> None:
        assert MarkdownUtils.convert_line_to_markdown("   ", ConversionOptions()) == ""


class TestApplyEmphasis:
    def test_bold_only(self) -> None:
        assert MarkdownUtils.apply_emphasis("word", bold=True) == "**word**"

    def test_italic_only(self) -> None:
        assert MarkdownUtils.apply_emphasis("word", italic=True) == "*word*"

    def test_bold_and_italic(self) -> None:
        assert MarkdownUtils.apply_emphasis("word", bold=True, italic=True) == "***word***"

    def test_no_emphasis_returns_unchanged(self) -> None:
        assert MarkdownUtils.apply_emphasis("word") == "word"

    def test_keeps_outer_whitespace_outside_markers(self) -> None:
        assert MarkdownUtils.apply_emphasis(" word ", bold=True) == " **word** "

    def test_whitespace_only_unchanged(self) -> None:
        assert MarkdownUtils.apply_emphasis("   ", bold=True) == "   "

    def test_empty_unchanged(self) -> None:
        assert MarkdownUtils.apply_emphasis("", bold=True) == ""



class TestSlugifyHeading:
    @pytest.mark.parametrize(
        ("heading", "expected"),
        [
            ("Hello World", "hello-world"),
            ("Hello, World!", "hello-world"),
            ("1.2 Section", "12-section"),
            ("multiple   spaces", "multiple-spaces"),
            ("", "section"),
            ("!!!", "section"),
        ],
    )
    def test_slugify(self, heading: str, expected: str) -> None:
        assert MarkdownUtils.slugify_heading(heading) == expected


class TestGenerateTableOfContents:
    def test_nested_with_duplicate_anchors(self) -> None:
        markdown = "## A\n### B\n## A"
        assert MarkdownUtils.generate_table_of_contents(markdown) == "- [A](#a)\n  - [B](#b)\n- [A](#a-1)"

    def test_no_headings_returns_placeholder(self) -> None:
        result = MarkdownUtils.generate_table_of_contents("just text\nmore text")
        assert result == "_No structured table of contents could be generated automatically._"

    def test_ignores_level_one_heading(self) -> None:
        # Only ## through ###### are included in the table of contents.
        assert MarkdownUtils.generate_table_of_contents("# Title") == (
            "_No structured table of contents could be generated automatically._"
        )


class TestValueToText:
    def test_none_returns_empty(self) -> None:
        assert MarkdownUtils.value_to_text(None) == ""

    def test_datetime_formatting(self) -> None:
        moment = datetime(2024, 1, 2, 3, 4)
        assert MarkdownUtils.value_to_text(moment) == "2024-01-02 03:04"

    def test_collapses_whitespace(self) -> None:
        assert MarkdownUtils.value_to_text("  a  b  ") == "a b"


class TestPrettifyTitle:
    def test_replaces_separators(self) -> None:
        assert MarkdownUtils.prettify_title("my_report-final") == "my report final"

    def test_empty_returns_untitled(self) -> None:
        assert MarkdownUtils.prettify_title("   ") == "Untitled Document"


class TestRowsToMarkdownTable:
    def test_empty_returns_empty_string(self) -> None:
        assert MarkdownUtils.rows_to_markdown_table([]) == ""

    def test_basic_table(self) -> None:
        result = MarkdownUtils.rows_to_markdown_table([["a", "b"], ["c", "d"]])
        assert result == "| a | b |\n| --- | --- |\n| c | d |"

    def test_escapes_pipe(self) -> None:
        result = MarkdownUtils.rows_to_markdown_table([["a", "b"], ["c", "d|e"]])
        assert result == "| a | b |\n| --- | --- |\n| c | d\\|e |"

    def test_pads_ragged_rows(self) -> None:
        result = MarkdownUtils.rows_to_markdown_table([["a", "b", "c"], ["d"]])
        assert result == "| a | b | c |\n| --- | --- | --- |\n| d |  |  |"


class TestSanitizeMarkdown:
    def test_trims_and_collapses(self) -> None:
        assert MarkdownUtils.sanitize_markdown("\n\na\n\n\nb  \n\n") == "a\n\nb"


class TestUniqueOutputPath:
    def test_returns_same_when_not_exists(self, tmp_path) -> None:
        target = tmp_path / "out.md"
        assert MarkdownUtils.unique_output_path(target) == target

    def test_appends_index_when_exists(self, tmp_path) -> None:
        target = tmp_path / "out.md"
        target.write_text("x", encoding="utf-8")
        assert MarkdownUtils.unique_output_path(target) == tmp_path / "out_1.md"

    def test_skips_existing_indices(self, tmp_path) -> None:
        (tmp_path / "out.md").write_text("x", encoding="utf-8")
        (tmp_path / "out_1.md").write_text("x", encoding="utf-8")
        assert MarkdownUtils.unique_output_path(tmp_path / "out.md") == tmp_path / "out_2.md"


class TestTextToMarkdown:
    def test_empty_returns_empty(self) -> None:
        assert MarkdownUtils.text_to_markdown("   ", ConversionOptions()) == ""

    def test_joins_paragraph_lines(self) -> None:
        options = ConversionOptions(detect_headings=False)
        result = MarkdownUtils.text_to_markdown("line one\nline two", options)
        assert result == "line one line two"

    def test_separates_blocks_on_blank_line(self) -> None:
        options = ConversionOptions(detect_headings=False)
        result = MarkdownUtils.text_to_markdown("para one\n\npara two", options)
        assert result == "para one\n\npara two"
