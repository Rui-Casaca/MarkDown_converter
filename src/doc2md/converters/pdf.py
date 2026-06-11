"""PDF to Markdown converter with font-size aware heading detection."""

from __future__ import annotations

import importlib
import re
from collections.abc import Iterator
from pathlib import Path
from typing import Any

from ..dependencies import DependencyManager
from ..markdown_utils import MarkdownUtils
from ..models import PDF_DEPENDENCY, ConversionOptions
from .assets import AssetWriter, extension_from_name, image_markdown
from .base import DocumentToMarkdownConverter
from .comments import Comment, render_comment_callout
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

        self._comment_index_counter = 0
        pdf_text_boxes = (
            self._extract_pages_text_boxes(input_path) if self.options.include_comments else None
        )

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

            if self.options.include_comments:
                page_blocks.extend(self._extract_page_comments(page, index, pdf_text_boxes))

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

    # -- Review comments (PDF annotations) -------------------------------------

    def _extract_page_comments(
        self,
        page: Any,
        page_number: int,
        page_boxes: list[dict[str, list]] | None,
    ) -> list[str]:
        """Return rendered comment callouts for the annotations on a single page."""
        try:
            annotations = self._resolve(page.get("/Annots"))
        except Exception:
            annotations = None
        if not annotations:
            return []

        boxes = None
        if page_boxes is not None and 0 <= page_number - 1 < len(page_boxes):
            boxes = page_boxes[page_number - 1]

        comments_by_key: dict[tuple[int, int], Comment] = {}
        ordered: list[tuple[tuple[int, int] | None, Comment]] = []
        for reference in annotations:
            annotation = self._resolve(reference)
            if not hasattr(annotation, "get"):
                continue
            subtype = str(annotation.get("/Subtype", "") or "")
            if subtype in ("/Popup", "/Link"):
                continue

            note = self._annotation_text(annotation.get("/Contents"))
            subject = self._annotation_text(annotation.get("/Subj"))
            anchor = self._annotation_anchor(annotation, boxes)
            text = note or subject
            if not text and not anchor:
                continue

            comment = Comment(
                author=self._annotation_text(annotation.get("/T")),
                date=self._format_pdf_date(self._annotation_text(annotation.get("/M"))),
                anchor_text=anchor,
                text=text,
                location=f"page {page_number}",
                resolved=self._annotation_resolved(annotation),
            )
            key = self._reference_key(reference)
            if key is not None:
                comments_by_key[key] = comment
            parent_value = annotation.get("/IRT")
            parent_key = self._reference_key(parent_value) if parent_value is not None else None
            ordered.append((parent_key, comment))

        top_level: list[Comment] = []
        for parent_key, comment in ordered:
            parent = comments_by_key.get(parent_key) if parent_key is not None else None
            if parent is not None and parent is not comment:
                parent.replies.append(comment)
            else:
                top_level.append(comment)

        callouts: list[str] = []
        for comment in top_level:
            self._comment_index_counter += 1
            comment.index = self._comment_index_counter
            callouts.append(render_comment_callout(comment))
        return callouts

    @staticmethod
    def _resolve(value: Any) -> Any:
        getter = getattr(value, "get_object", None)
        if callable(getter):
            try:
                return getter()
            except Exception:
                return value
        return value

    @staticmethod
    def _reference_key(reference: Any) -> tuple[int, int] | None:
        idnum = getattr(reference, "idnum", None)
        if idnum is None:
            return None
        return (int(idnum), int(getattr(reference, "generation", 0) or 0))

    def _annotation_text(self, value: Any) -> str:
        value = self._resolve(value)
        if value is None:
            return ""
        if isinstance(value, bytes):
            for encoding in ("utf-16", "utf-8", "latin-1"):
                try:
                    return MarkdownUtils.value_to_text(value.decode(encoding))
                except Exception:
                    continue
            return ""
        return MarkdownUtils.value_to_text(str(value))

    def _annotation_resolved(self, annotation: Any) -> bool:
        state = self._annotation_text(annotation.get("/State")).lower()
        return state in ("completed", "accepted", "resolved")

    def _annotation_anchor(self, annotation: Any, boxes: dict[str, list] | None) -> str:
        if boxes is None:
            return ""
        quad_points = self._resolve(annotation.get("/QuadPoints"))
        if quad_points:
            try:
                text = self._text_in_quads([float(value) for value in quad_points], boxes["chars"])
            except Exception:
                text = ""
            if text:
                return text
        rectangle = self._resolve(annotation.get("/Rect"))
        if rectangle:
            try:
                return self._nearest_line_text([float(value) for value in rectangle], boxes["lines"])
            except Exception:
                return ""
        return ""

    @staticmethod
    def _text_in_quads(quad: list[float], chars: list[tuple[str, float, float]]) -> str:
        regions: list[tuple[float, float, float, float]] = []
        for start in range(0, len(quad) - 7, 8):
            xs = quad[start : start + 8 : 2]
            ys = quad[start + 1 : start + 8 : 2]
            regions.append((min(xs), min(ys), max(xs), max(ys)))
        if not regions:
            return ""
        selected: list[tuple[float, float, str]] = []
        for character, center_x, center_y in chars:
            for x0, y0, x1, y1 in regions:
                if x0 - 1 <= center_x <= x1 + 1 and y0 - 1 <= center_y <= y1 + 1:
                    selected.append((center_y, center_x, character))
                    break
        if not selected:
            return ""
        selected.sort(key=lambda item: (-round(item[0]), item[1]))
        return "".join(item[2] for item in selected).strip()

    @staticmethod
    def _nearest_line_text(
        rectangle: list[float],
        lines: list[tuple[str, float, float, float, float]],
    ) -> str:
        if not lines or len(rectangle) < 4:
            return ""
        rect_center_y = (rectangle[1] + rectangle[3]) / 2.0
        best_text = ""
        best_distance: float | None = None
        for text, _x0, y0, _x1, y1 in lines:
            distance = abs((y0 + y1) / 2.0 - rect_center_y)
            if best_distance is None or distance < best_distance:
                best_distance = distance
                best_text = text
        return best_text

    @staticmethod
    def _extract_pages_text_boxes(input_path: Path) -> list[dict[str, list]] | None:
        """Return per-page text-line boxes and character centers for annotation anchoring."""
        try:
            high_level = importlib.import_module("pdfminer.high_level")
            layout = importlib.import_module("pdfminer.layout")
        except Exception:
            return None

        text_container = layout.LTTextContainer
        text_line = layout.LTTextLine
        char_type = layout.LTChar
        laparams = layout.LAParams()

        pages: list[dict[str, list]] = []
        try:
            for page_layout in high_level.extract_pages(str(input_path), laparams=laparams):
                lines: list[tuple[str, float, float, float, float]] = []
                chars: list[tuple[str, float, float]] = []
                for element in page_layout:
                    if not isinstance(element, text_container):
                        continue
                    for line in element:
                        if not isinstance(line, text_line):
                            continue
                        text = line.get_text().strip()
                        if text:
                            x0, y0, x1, y1 = line.bbox
                            lines.append((text, x0, y0, x1, y1))
                        for character in line:
                            if isinstance(character, char_type):
                                cx0, cy0, cx1, cy1 = character.bbox
                                chars.append(
                                    (character.get_text(), (cx0 + cx1) / 2.0, (cy0 + cy1) / 2.0)
                                )
                pages.append({"lines": lines, "chars": chars})
        except Exception:
            return None
        return pages

    @staticmethod
    def _format_pdf_date(value: str) -> str:
        value = (value or "").strip()
        if not value:
            return ""
        match = re.match(r"D?:?\s*(\d{4})(\d{2})?(\d{2})?(\d{2})?(\d{2})?", value)
        if not match:
            return value
        year, month, day, hour, minute = match.groups()
        date_part = "-".join(part for part in (year, month, day) if part)
        if hour and minute:
            return f"{date_part} {hour}:{minute}"
        return date_part

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
