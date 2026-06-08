"""PDF to Markdown converter with font-size aware heading detection."""

from __future__ import annotations

import importlib
from collections.abc import Iterator
from pathlib import Path
from typing import Any

from ..dependencies import DependencyManager
from ..markdown_utils import MarkdownUtils
from ..models import PDF_DEPENDENCY, ConversionOptions
from .assets import AssetWriter, extension_from_name, image_markdown
from .base import DocumentToMarkdownConverter
from .ocr import OcrEngine

# Lines this many times larger than the body text are treated as headings.
HEADING_SIZE_RATIOS: tuple[tuple[float, int], ...] = (
    (1.8, 2),
    (1.45, 3),
    (1.2, 4),
)
MAX_HEADING_WORDS = 14


class PdfMarkdownConverter(DocumentToMarkdownConverter):
    dependency = PDF_DEPENDENCY
    source_type = "PDF"

    def __init__(self, options: ConversionOptions, dependency_manager: DependencyManager) -> None:
        super().__init__(options, dependency_manager)
        self._ocr_engine_instance: OcrEngine | None = None

    def extract(
        self,
        input_path: Path,
        asset_writer: AssetWriter | None = None,
    ) -> tuple[str, dict[str, str], str]:
        pdf_module = importlib.import_module("pypdf")
        reader = pdf_module.PdfReader(str(input_path))
        metadata = getattr(reader, "metadata", None)
        total_pages = len(reader.pages)
        extracted_title = self._metadata_value(metadata, "/Title")

        extra_metadata: dict[str, str] = {}
        if self.options.include_metadata:
            extra_metadata["Pages"] = str(total_pages)
            extra_metadata["Author"] = self._metadata_value(metadata, "/Author")
            extra_metadata["Subject"] = self._metadata_value(metadata, "/Subject")
            extra_metadata["Title"] = extracted_title
            extra_metadata["Creator"] = self._metadata_value(metadata, "/Creator")
            extra_metadata["Producer"] = self._metadata_value(metadata, "/Producer")

        title = extracted_title or MarkdownUtils.prettify_title(input_path.stem)

        pages_lines = None
        if self.options.detect_headings:
            pages_lines = self._extract_pages_with_sizes(input_path)
        body_size = self._estimate_body_size(pages_lines) if pages_lines else 0.0

        page_blocks: list[str] = []
        for index, page in enumerate(reader.pages, start=1):
            if self.options.include_page_slide_separators:
                if page_blocks:
                    page_blocks.append("")
                page_blocks.extend(["---", f"<!-- Page {index} -->", ""])

            page_markdown = ""
            if pages_lines is not None and index - 1 < len(pages_lines):
                page_markdown = self._render_page_from_lines(pages_lines[index - 1], body_size)

            if not page_markdown:
                try:
                    raw_text = page.extract_text() or ""
                except Exception:
                    raw_text = ""
                page_markdown = MarkdownUtils.text_to_markdown(raw_text, self.options)

            if not page_markdown and self.options.enable_ocr:
                ocr_text = self._ocr_page(page)
                if ocr_text:
                    page_markdown = MarkdownUtils.text_to_markdown(ocr_text, self.options)

            if page_markdown:
                page_blocks.append(page_markdown)
            else:
                page_blocks.append("_No selectable text was found on this page. OCR may be required._")

            if asset_writer is not None:
                page_blocks.extend(self._extract_page_images(page, asset_writer))

        content = "\n\n".join(block for block in page_blocks if block.strip())
        if not content:
            content = "_No selectable text was extracted from this PDF. OCR may be required._"

        return title, extra_metadata, content

    def _ocr_engine(self) -> OcrEngine:
        if self._ocr_engine_instance is None:
            self._ocr_engine_instance = OcrEngine()
        return self._ocr_engine_instance

    def _ocr_page(self, page: Any) -> str:
        engine = self._ocr_engine()
        if not engine.is_available():
            return ""

        texts: list[str] = []
        for image in self._iter_page_pil_images(page):
            recognized = engine.image_to_text(image)
            if recognized:
                texts.append(recognized)
        return "\n".join(texts)

    @staticmethod
    def _iter_page_pil_images(page: Any) -> Iterator[Any]:
        try:
            images = list(page.images)
        except Exception:
            return
        for image_file in images:
            pil_image = getattr(image_file, "image", None)
            if pil_image is not None:
                yield pil_image

    @staticmethod
    def _extract_page_images(page: Any, asset_writer: AssetWriter) -> list[str]:
        refs: list[str] = []
        try:
            images = list(page.images)
        except Exception:
            return refs
        for image_file in images:
            data = getattr(image_file, "data", None)
            name = getattr(image_file, "name", "")
            relative_path = asset_writer.save_image(data, extension_from_name(name))
            if relative_path:
                refs.append(image_markdown(relative_path))
        return refs

    @staticmethod
    def _extract_pages_with_sizes(input_path: Path) -> list[list[tuple[str, float]]] | None:
        """Return per-page lists of (line_text, font_size) using pdfminer, or None on failure."""
        try:
            high_level = importlib.import_module("pdfminer.high_level")
            layout = importlib.import_module("pdfminer.layout")
        except Exception:
            return None

        text_container = layout.LTTextContainer
        text_line = layout.LTTextLine
        char_type = layout.LTChar
        laparams = layout.LAParams()

        pages: list[list[tuple[str, float]]] = []
        try:
            for page_layout in high_level.extract_pages(str(input_path), laparams=laparams):
                lines: list[tuple[str, float]] = []
                for element in page_layout:
                    if not isinstance(element, text_container):
                        continue
                    for line in element:
                        if not isinstance(line, text_line):
                            continue
                        text = line.get_text().strip()
                        sizes = [char.size for char in line if isinstance(char, char_type)]
                        if not text or not sizes:
                            continue
                        lines.append((text, _median(sizes)))
                pages.append(lines)
        except Exception:
            return None

        return pages

    @staticmethod
    def _estimate_body_size(pages_lines: list[list[tuple[str, float]]]) -> float:
        """Estimate the dominant body font size, weighted by characters of text."""
        weights: dict[int, int] = {}
        for lines in pages_lines:
            for text, size in lines:
                key = round(size)
                weights[key] = weights.get(key, 0) + len(text)
        if not weights:
            return 0.0
        return float(max(weights, key=lambda key: weights[key]))

    @staticmethod
    def _heading_level_for_size(size: float, body_size: float) -> int:
        if body_size <= 0:
            return 0
        ratio = size / body_size
        for threshold, level in HEADING_SIZE_RATIOS:
            if ratio >= threshold:
                return level
        return 0

    def _render_page_from_lines(
        self,
        lines: list[tuple[str, float]],
        body_size: float,
    ) -> str:
        blocks: list[str] = []
        paragraph_lines: list[str] = []

        def flush_paragraph() -> None:
            if not paragraph_lines:
                return
            block = MarkdownUtils.text_to_markdown("\n".join(paragraph_lines), self.options)
            if block:
                blocks.append(block)
            paragraph_lines.clear()

        for text, size in lines:
            level = self._heading_level_for_size(size, body_size)
            if level and len(text.split()) <= MAX_HEADING_WORDS:
                flush_paragraph()
                clean_heading = text.strip(" .")
                blocks.append(f"{'#' * level} {clean_heading}")
            else:
                paragraph_lines.append(text)

        flush_paragraph()
        return "\n\n".join(block for block in blocks if block.strip())

    @staticmethod
    def _metadata_value(metadata: object, key: str) -> str:
        if metadata is None:
            return ""

        try:
            if hasattr(metadata, "get"):
                value = metadata.get(key, "")
                if value:
                    return MarkdownUtils.value_to_text(value)
        except Exception:
            pass

        attr_name = key.strip("/").lower()
        try:
            value = getattr(metadata, attr_name, "")
            return MarkdownUtils.value_to_text(value)
        except Exception:
            return ""


def _median(values: list[float]) -> float:
    ordered = sorted(values)
    count = len(ordered)
    if count == 0:
        return 0.0
    middle = count // 2
    if count % 2 == 1:
        return float(ordered[middle])
    return (ordered[middle - 1] + ordered[middle]) / 2.0
