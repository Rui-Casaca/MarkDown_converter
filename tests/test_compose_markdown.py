"""Tests for header/TOC/front-matter composition in the converter base."""

from __future__ import annotations

from pathlib import Path

from doc2md.converters.pdf import PdfMarkdownConverter
from doc2md.dependencies import DependencyManager
from doc2md.models import (
    DOCX_DEPENDENCY,
    HEADER_STYLE_BLOCKQUOTE,
    HEADER_STYLE_YAML,
    PDF_DEPENDENCY,
    PPTX_DEPENDENCY,
    ConversionOptions,
)

ALL_DEPENDENCIES = [PDF_DEPENDENCY, DOCX_DEPENDENCY, PPTX_DEPENDENCY]


def _compose(
    options: ConversionOptions,
    *,
    title: str = "My Title",
    content: str = "## Section\n\nBody.",
) -> str:
    manager = DependencyManager(ALL_DEPENDENCIES)
    converter = PdfMarkdownConverter(options, manager)
    return converter._compose_markdown(
        input_path=Path("report.pdf"),
        title=title,
        metadata={"Author": "Jane", "Subject": ""},
        content=content,
    )


class TestBlockquoteHeader:
    def test_default_includes_blockquote_header(self) -> None:
        result = _compose(ConversionOptions())
        assert "> Converted to Markdown." in result
        assert "> Source file: `report.pdf`" in result
        assert "> Source type: PDF" in result

    def test_includes_metadata_when_enabled(self) -> None:
        result = _compose(ConversionOptions(include_metadata=True))
        assert "> Author: Jane" in result

    def test_skips_empty_metadata_values(self) -> None:
        result = _compose(ConversionOptions(include_metadata=True))
        assert "Subject" not in result

    def test_excludes_metadata_when_disabled(self) -> None:
        result = _compose(ConversionOptions(include_metadata=False))
        assert "Author" not in result
        assert "> Converted to Markdown." in result


class TestToc:
    def test_toc_present_by_default(self) -> None:
        result = _compose(ConversionOptions())
        assert "## Table of Contents" in result

    def test_toc_absent_when_disabled(self) -> None:
        result = _compose(ConversionOptions(include_toc=False))
        assert "## Table of Contents" not in result
        assert "## Content" in result


class TestHeaderToggle:
    def test_no_header_block_when_disabled(self) -> None:
        result = _compose(ConversionOptions(include_header=False))
        assert "> Converted to Markdown." not in result
        assert result.startswith("# My Title")

    def test_clean_output_no_header_no_toc(self) -> None:
        result = _compose(ConversionOptions(include_header=False, include_toc=False))
        assert "Table of Contents" not in result
        assert "> Converted" not in result
        assert "## Content" in result


class TestYamlFrontMatter:
    def test_front_matter_at_top(self) -> None:
        result = _compose(ConversionOptions(header_style=HEADER_STYLE_YAML))
        assert result.startswith("---\n")
        assert 'title: "My Title"' in result
        assert 'source_file: "report.pdf"' in result
        assert 'source_type: "PDF"' in result

    def test_front_matter_precedes_title_heading(self) -> None:
        result = _compose(ConversionOptions(header_style=HEADER_STYLE_YAML))
        yaml_end = result.index("---", 3)
        title_pos = result.index("# My Title")
        assert yaml_end < title_pos

    def test_no_blockquote_in_yaml_mode(self) -> None:
        result = _compose(ConversionOptions(header_style=HEADER_STYLE_YAML))
        assert "> Converted to Markdown." not in result

    def test_yaml_disabled_when_header_excluded(self) -> None:
        result = _compose(
            ConversionOptions(include_header=False, header_style=HEADER_STYLE_YAML)
        )
        assert not result.startswith("---")
        assert result.startswith("# My Title")

    def test_metadata_keys_are_snake_cased(self) -> None:
        manager = DependencyManager(ALL_DEPENDENCIES)
        converter = PdfMarkdownConverter(
            ConversionOptions(header_style=HEADER_STYLE_YAML), manager
        )
        result = converter._compose_markdown(
            input_path=Path("a.pdf"),
            title="T",
            metadata={"Last modified by": "Bob"},
            content="Body.",
        )
        assert 'last_modified_by: "Bob"' in result


class TestYamlScalarEscaping:
    def test_escapes_double_quotes_and_backslashes(self) -> None:
        result = _compose(
            ConversionOptions(header_style=HEADER_STYLE_YAML),
            title='Quote " and \\ slash',
        )
        assert 'title: "Quote \\" and \\\\ slash"' in result

    def test_title_with_colon_is_quoted(self) -> None:
        result = _compose(
            ConversionOptions(header_style=HEADER_STYLE_YAML),
            title="Chapter: One",
        )
        assert 'title: "Chapter: One"' in result


class TestStructuralInvariants:
    def test_content_and_footer_always_present(self) -> None:
        for options in [
            ConversionOptions(),
            ConversionOptions(header_style=HEADER_STYLE_YAML),
            ConversionOptions(include_header=False, include_toc=False),
        ]:
            result = _compose(options)
            assert "## Content" in result
            assert "_Conversion completed by Document to Markdown Converter._" in result

    def test_trailing_newline(self) -> None:
        assert _compose(ConversionOptions()).endswith("\n")

    def test_default_style_is_blockquote(self) -> None:
        assert ConversionOptions().header_style == HEADER_STYLE_BLOCKQUOTE
