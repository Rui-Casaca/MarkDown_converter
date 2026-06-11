"""Integration tests for the document converters."""

from __future__ import annotations

from pathlib import Path

import pytest

from doc2md.converters import (
    DocxMarkdownConverter,
    PdfMarkdownConverter,
    PptxMarkdownConverter,
    get_converter_for_path,
)
from doc2md.dependencies import DependencyManager
from doc2md.models import (
    DOCX_DEPENDENCY,
    PDF_DEPENDENCY,
    PPTX_DEPENDENCY,
    SOURCE_TYPE_BY_EXTENSION,
    ConversionJob,
    ConversionOptions,
)

ALL_DEPENDENCIES = [PDF_DEPENDENCY, DOCX_DEPENDENCY, PPTX_DEPENDENCY]


def _make_job(source: Path, output: Path) -> ConversionJob:
    return ConversionJob(
        input_path=source,
        output_path=output,
        source_type=SOURCE_TYPE_BY_EXTENSION[source.suffix.lower()],
    )


class TestFactory:
    def test_returns_pdf_converter(self, tmp_path: Path) -> None:
        manager = DependencyManager(ALL_DEPENDENCIES)
        converter = get_converter_for_path(tmp_path / "a.pdf", ConversionOptions(), manager)
        assert isinstance(converter, PdfMarkdownConverter)

    def test_returns_docx_converter(self, tmp_path: Path) -> None:
        manager = DependencyManager(ALL_DEPENDENCIES)
        converter = get_converter_for_path(tmp_path / "a.docx", ConversionOptions(), manager)
        assert isinstance(converter, DocxMarkdownConverter)

    def test_returns_pptx_converter(self, tmp_path: Path) -> None:
        manager = DependencyManager(ALL_DEPENDENCIES)
        converter = get_converter_for_path(tmp_path / "a.pptx", ConversionOptions(), manager)
        assert isinstance(converter, PptxMarkdownConverter)

    def test_unsupported_extension_raises(self, tmp_path: Path) -> None:
        manager = DependencyManager(ALL_DEPENDENCIES)
        with pytest.raises(ValueError, match="Unsupported file type"):
            get_converter_for_path(tmp_path / "a.txt", ConversionOptions(), manager)


class TestConvertBase:
    def test_missing_input_file_fails_gracefully(self, tmp_path: Path) -> None:
        manager = DependencyManager(ALL_DEPENDENCIES)
        converter = DocxMarkdownConverter(ConversionOptions(), manager)
        job = _make_job(tmp_path / "missing.docx", tmp_path / "out.md")
        result = converter.convert(job)
        assert result.success is False
        assert "does not exist" in result.message


class TestDocxConversion:
    def test_converts_and_writes_output(self, docx_file: Path, tmp_path: Path) -> None:
        manager = DependencyManager(ALL_DEPENDENCIES)
        converter = DocxMarkdownConverter(ConversionOptions(), manager)
        output = tmp_path / "out.md"
        result = converter.convert(_make_job(docx_file, output))

        assert result.success is True
        assert output.exists()

    def test_output_contains_expected_blocks(self, docx_file: Path, tmp_path: Path) -> None:
        manager = DependencyManager(ALL_DEPENDENCIES)
        converter = DocxMarkdownConverter(ConversionOptions(), manager)
        output = tmp_path / "out.md"
        converter.convert(_make_job(docx_file, output))
        text = output.read_text(encoding="utf-8")

        assert "## Title One" in text
        assert "Hello world paragraph." in text
        assert "- Bullet item" in text
        assert "| H1 | H2 |" in text


class TestPptxConversion:
    def test_converts_and_writes_output(self, pptx_file: Path, tmp_path: Path) -> None:
        manager = DependencyManager(ALL_DEPENDENCIES)
        converter = PptxMarkdownConverter(ConversionOptions(), manager)
        output = tmp_path / "out.md"
        result = converter.convert(_make_job(pptx_file, output))

        assert result.success is True
        assert output.exists()

    def test_output_contains_slide_title_and_body(self, pptx_file: Path, tmp_path: Path) -> None:
        manager = DependencyManager(ALL_DEPENDENCIES)
        converter = PptxMarkdownConverter(ConversionOptions(), manager)
        output = tmp_path / "out.md"
        converter.convert(_make_job(pptx_file, output))
        text = output.read_text(encoding="utf-8")

        assert "## Slide Title" in text
        assert "Body line" in text
        assert "<!-- Slide 1 -->" in text


class TestPdfMetadataValue:
    def test_none_metadata(self) -> None:
        assert PdfMarkdownConverter._metadata_value(None, "/Title") == ""

    def test_dict_like_metadata(self) -> None:
        assert PdfMarkdownConverter._metadata_value({"/Title": "My Doc"}, "/Title") == "My Doc"

    def test_missing_key_returns_empty(self) -> None:
        assert PdfMarkdownConverter._metadata_value({"/Author": "A"}, "/Title") == ""


class TestDocxInlineFormatting:
    def test_preserves_bold_italic_and_link(self, rich_docx_file, tmp_path) -> None:
        manager = DependencyManager(ALL_DEPENDENCIES)
        converter = DocxMarkdownConverter(ConversionOptions(), manager)
        output = tmp_path / "rich.md"
        converter.convert(_make_job(rich_docx_file, output))
        text = output.read_text(encoding="utf-8")

        assert "**bolded**" in text
        assert "*slanted*" in text
        assert "[the link](https://example.com)" in text


class TestPptxInlineFormatting:
    def test_preserves_bold_italic_and_link(self, rich_pptx_file, tmp_path) -> None:
        manager = DependencyManager(ALL_DEPENDENCIES)
        converter = PptxMarkdownConverter(ConversionOptions(), manager)
        output = tmp_path / "rich.md"
        converter.convert(_make_job(rich_pptx_file, output))
        text = output.read_text(encoding="utf-8")

        assert "**Bolded**" in text
        assert "*Slanted*" in text
        assert "[linked](https://example.org)" in text


class TestPdfFontHeadingHelpers:
    PAGES = [
        [
            ("Big Title", 20.0),
            ("body line one", 10.0),
            ("body line two", 10.0),
            ("Sub Heading", 14.0),
            ("more body text here", 10.0),
        ]
    ]

    def test_estimate_body_size_picks_dominant(self) -> None:
        assert PdfMarkdownConverter._estimate_body_size(self.PAGES) == 10.0

    def test_estimate_body_size_empty(self) -> None:
        assert PdfMarkdownConverter._estimate_body_size([]) == 0.0

    @pytest.mark.parametrize(
        ("size", "expected_level"),
        [
            (20.0, 2),
            (15.0, 3),
            (12.5, 4),
            (10.0, 0),
        ],
    )
    def test_heading_level_for_size(self, size: float, expected_level: int) -> None:
        assert PdfMarkdownConverter._heading_level_for_size(size, 10.0) == expected_level

    def test_heading_level_zero_body_size(self) -> None:
        assert PdfMarkdownConverter._heading_level_for_size(20.0, 0.0) == 0

    def test_render_page_emits_headings_and_paragraphs(self) -> None:
        manager = DependencyManager(ALL_DEPENDENCIES)
        converter = PdfMarkdownConverter(ConversionOptions(), manager)
        rendered = converter._render_page_from_lines(self.PAGES[0], 10.0)

        assert "## Big Title" in rendered
        assert "#### Sub Heading" in rendered
        assert "body line one body line two" in rendered

    def test_render_page_without_detection_when_body_size_zero(self) -> None:
        manager = DependencyManager(ALL_DEPENDENCIES)
        converter = PdfMarkdownConverter(ConversionOptions(detect_headings=False), manager)
        rendered = converter._render_page_from_lines(self.PAGES[0], 0.0)

        assert "#" not in rendered
        assert "Big Title" in rendered


class TestDocxImageExtraction:
    def test_emits_reference_and_writes_file(self, docx_with_image, tmp_path) -> None:
        manager = DependencyManager(ALL_DEPENDENCIES)
        converter = DocxMarkdownConverter(ConversionOptions(extract_images=True), manager)
        output = tmp_path / "out.md"
        converter.convert(_make_job(docx_with_image, output))
        text = output.read_text(encoding="utf-8")

        assert "![](out_assets/image_1.png)" in text
        assert (tmp_path / "out_assets" / "image_1.png").exists()

    def test_no_assets_when_disabled(self, docx_with_image, tmp_path) -> None:
        manager = DependencyManager(ALL_DEPENDENCIES)
        converter = DocxMarkdownConverter(ConversionOptions(extract_images=False), manager)
        output = tmp_path / "out.md"
        converter.convert(_make_job(docx_with_image, output))

        assert "![](" not in output.read_text(encoding="utf-8")
        assert not (tmp_path / "out_assets").exists()


class TestPptxImageExtraction:
    def test_emits_reference_and_writes_file(self, pptx_with_image, tmp_path) -> None:
        manager = DependencyManager(ALL_DEPENDENCIES)
        converter = PptxMarkdownConverter(ConversionOptions(extract_images=True), manager)
        output = tmp_path / "out.md"
        converter.convert(_make_job(pptx_with_image, output))
        text = output.read_text(encoding="utf-8")

        assert "![](out_assets/image_1.png)" in text
        assert (tmp_path / "out_assets" / "image_1.png").exists()


class TestDocxComments:
    def test_anchors_inline_and_renders_callout(self, docx_with_comments, tmp_path) -> None:
        manager = DependencyManager(ALL_DEPENDENCIES)
        converter = DocxMarkdownConverter(ConversionOptions(include_comments=True), manager)
        output = tmp_path / "out.md"
        converter.convert(_make_job(docx_with_comments, output))
        text = output.read_text(encoding="utf-8")

        assert "\u27e6grew by 12%\u27e7\u00b9" in text
        assert "[!COMMENT] Comment 1 \u2014 Jane Doe" in text
        assert '**About:** "grew by 12%"' in text
        assert "**Note:** Please verify this figure." in text

    def test_comments_disabled_by_default(self, docx_with_comments, tmp_path) -> None:
        manager = DependencyManager(ALL_DEPENDENCIES)
        converter = DocxMarkdownConverter(ConversionOptions(), manager)
        output = tmp_path / "out.md"
        converter.convert(_make_job(docx_with_comments, output))
        text = output.read_text(encoding="utf-8")

        assert "[!COMMENT]" not in text
        assert "\u27e6" not in text


class TestPdfCommentHelpers:
    def test_format_pdf_date_full(self) -> None:
        assert PdfMarkdownConverter._format_pdf_date("D:20240512103000Z") == "2024-05-12 10:30"

    def test_format_pdf_date_date_only(self) -> None:
        assert PdfMarkdownConverter._format_pdf_date("D:20240512") == "2024-05-12"

    def test_format_pdf_date_empty(self) -> None:
        assert PdfMarkdownConverter._format_pdf_date("") == ""

    def test_text_in_quads_selects_chars_in_reading_order(self) -> None:
        chars = [("H", 10.0, 100.0), ("i", 20.0, 100.0), ("X", 500.0, 100.0)]
        quad = [0.0, 90.0, 100.0, 90.0, 0.0, 110.0, 100.0, 110.0]
        assert PdfMarkdownConverter._text_in_quads(quad, chars) == "Hi"

    def test_nearest_line_text_picks_closest(self) -> None:
        lines = [
            ("top line", 0.0, 700.0, 100.0, 720.0),
            ("bottom line", 0.0, 100.0, 100.0, 120.0),
        ]
        assert PdfMarkdownConverter._nearest_line_text([0.0, 695.0, 100.0, 715.0], lines) == "top line"
