"""Tests for the shared comment model and Markdown rendering."""

from __future__ import annotations

from doc2md.converters.comments import (
    Comment,
    render_comment_callout,
    shorten_anchor,
    superscript,
)


class TestSuperscript:
    def test_single_digit(self) -> None:
        assert superscript(1) == "\u00b9"

    def test_multi_digit(self) -> None:
        assert superscript(12) == "\u00b9\u00b2"


class TestShortenAnchor:
    def test_collapses_whitespace(self) -> None:
        assert shorten_anchor("  a\n   b\t c ") == "a b c"

    def test_trims_long_text(self) -> None:
        result = shorten_anchor("x" * 400)
        assert len(result) <= 280
        assert result.endswith("\u2026")

    def test_empty(self) -> None:
        assert shorten_anchor("") == ""


class TestRenderCommentCallout:
    def test_basic_callout(self) -> None:
        comment = Comment(
            index=1,
            author="Jane Doe",
            date="2024-05-12",
            anchor_text="grew by 12%",
            text="Please verify this figure.",
        )
        rendered = render_comment_callout(comment)

        assert rendered.splitlines()[0] == "> [!COMMENT] Comment 1 \u2014 Jane Doe (2024-05-12)"
        assert '> **About:** "grew by 12%"' in rendered
        assert "> **Note:** Please verify this figure." in rendered

    def test_resolved_and_location_in_header(self) -> None:
        comment = Comment(index=2, author="Bob", text="ok", location="page 3", resolved=True)
        header = render_comment_callout(comment).splitlines()[0]

        assert "page 3" in header
        assert "resolved" in header

    def test_missing_anchor_omits_about(self) -> None:
        rendered = render_comment_callout(Comment(index=1, text="note only"))

        assert "About:" not in rendered
        assert "> **Note:** note only" in rendered

    def test_nested_replies(self) -> None:
        parent = Comment(
            index=1,
            author="Alice",
            text="parent note",
            replies=[Comment(author="Bob", date="2024-01-01", text="child note")],
        )
        rendered = render_comment_callout(parent)

        assert "> > **Reply \u2014 Bob (2024-01-01)**" in rendered
        assert "> > child note" in rendered

    def test_multiline_note(self) -> None:
        rendered = render_comment_callout(Comment(index=1, text="line one\nline two"))

        assert "> **Note:** line one" in rendered
        assert "> line two" in rendered

    def test_author_only_header(self) -> None:
        header = render_comment_callout(Comment(index=4, author="Solo")).splitlines()[0]

        assert header == "> [!COMMENT] Comment 4 \u2014 Solo"
