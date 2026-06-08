"""PowerPoint PPTX to Markdown converter."""

from __future__ import annotations

import importlib
from pathlib import Path

from ..markdown_utils import MarkdownUtils
from ..models import PPTX_DEPENDENCY
from .assets import AssetWriter, image_markdown, normalize_extension
from .base import DocumentToMarkdownConverter


class PptxMarkdownConverter(DocumentToMarkdownConverter):
    dependency = PPTX_DEPENDENCY
    source_type = "PowerPoint PPTX"

    def extract(
        self,
        input_path: Path,
        asset_writer: AssetWriter | None = None,
    ) -> tuple[str, dict[str, str], str]:
        pptx_module = importlib.import_module("pptx")
        presentation = pptx_module.Presentation(str(input_path))
        core_properties = presentation.core_properties
        slide_count = len(presentation.slides)
        extracted_title = MarkdownUtils.value_to_text(core_properties.title)

        extra_metadata: dict[str, str] = {}
        if self.options.include_metadata:
            extra_metadata["Slides"] = str(slide_count)
            extra_metadata["Author"] = MarkdownUtils.value_to_text(core_properties.author)
            extra_metadata["Subject"] = MarkdownUtils.value_to_text(core_properties.subject)
            extra_metadata["Title"] = extracted_title
            extra_metadata["Comments"] = MarkdownUtils.value_to_text(core_properties.comments)
            extra_metadata["Last modified by"] = MarkdownUtils.value_to_text(core_properties.last_modified_by)
            extra_metadata["Created"] = MarkdownUtils.value_to_text(core_properties.created)
            extra_metadata["Modified"] = MarkdownUtils.value_to_text(core_properties.modified)

        title = extracted_title or MarkdownUtils.prettify_title(input_path.stem)
        slide_blocks: list[str] = []

        for index, slide in enumerate(presentation.slides, start=1):
            title_text, title_shape_id, fallback_title = self._extract_slide_title(slide)
            slide_lines: list[str] = []
            used_fallback_title = False

            if self.options.include_page_slide_separators:
                if slide_blocks:
                    slide_blocks.append("")
                slide_blocks.extend(["---", f"<!-- Slide {index} -->", ""])

            slide_heading = title_text or f"Slide {index}"
            slide_lines.append(f"## {slide_heading}")

            for shape in slide.shapes:
                if title_shape_id is not None and getattr(shape, "shape_id", None) == title_shape_id:
                    continue

                if getattr(shape, "has_table", False):
                    markdown_table = self._pptx_table_to_markdown(shape.table)
                    if markdown_table:
                        slide_lines.append(markdown_table)
                    continue

                if asset_writer is not None:
                    image_reference = self._shape_image(shape, asset_writer)
                    if image_reference:
                        slide_lines.append(image_reference)

                if not getattr(shape, "has_text_frame", False):
                    continue

                text_block_lines: list[str] = []
                for paragraph in shape.text_frame.paragraphs:
                    paragraph_text = MarkdownUtils.value_to_text(paragraph.text)
                    if self.options.normalize_whitespace or self.options.optimize_for_ai:
                        paragraph_text = MarkdownUtils.value_to_text(
                            MarkdownUtils.normalize_text(paragraph_text)
                        )

                    if not paragraph_text:
                        continue
                    if (
                        title_shape_id is None
                        and fallback_title
                        and paragraph_text == fallback_title
                        and not used_fallback_title
                    ):
                        used_fallback_title = True
                        continue

                    text_block_lines.append(
                        self._paragraph_to_markdown(paragraph, paragraph_text)
                    )

                text_block = "\n".join(MarkdownUtils.remove_repeated_empty_lines(text_block_lines)).strip()
                if text_block:
                    slide_lines.append(text_block)

            slide_content = "\n\n".join(line for line in slide_lines if line.strip())
            if slide_content.strip() == f"## {slide_heading}":
                slide_content = f"## {slide_heading}\n\n_No extractable text was found on this slide._"

            slide_blocks.append(slide_content)

        content = "\n\n".join(block for block in slide_blocks if block.strip())
        if not content:
            content = "_No extractable text was found in this PowerPoint presentation._"

        return title, extra_metadata, content

    def _extract_slide_title(self, slide: object) -> tuple[str, int | None, str | None]:
        title_shape = getattr(slide.shapes, "title", None)
        if title_shape is not None:
            title_text = MarkdownUtils.value_to_text(title_shape.text)
            if self.options.normalize_whitespace or self.options.optimize_for_ai:
                title_text = MarkdownUtils.value_to_text(MarkdownUtils.normalize_text(title_text))
            if title_text:
                return title_text, getattr(title_shape, "shape_id", None), None

        for shape in slide.shapes:
            if not getattr(shape, "has_text_frame", False):
                continue
            for paragraph in shape.text_frame.paragraphs:
                paragraph_text = MarkdownUtils.value_to_text(paragraph.text)
                if self.options.normalize_whitespace or self.options.optimize_for_ai:
                    paragraph_text = MarkdownUtils.value_to_text(MarkdownUtils.normalize_text(paragraph_text))
                if paragraph_text:
                    return paragraph_text, None, paragraph_text

        return "", None, None

    def _paragraph_to_markdown(self, paragraph: object, paragraph_text: str) -> str:
        inline = self._inline_to_markdown(paragraph)
        if self.options.normalize_whitespace or self.options.optimize_for_ai:
            inline = MarkdownUtils.value_to_text(MarkdownUtils.normalize_text(inline))
        content = inline or paragraph_text

        list_prefix = self._list_prefix_for_paragraph(paragraph)
        if list_prefix:
            return f"{list_prefix}{content}"
        return MarkdownUtils.convert_line_to_markdown(content, self.options)

    @staticmethod
    def _inline_to_markdown(paragraph: object) -> str:
        """Render a paragraph's runs, preserving bold, italic, and hyperlinks."""
        parts: list[str] = []
        for run in getattr(paragraph, "runs", []):
            text = getattr(run, "text", "") or ""
            if not text:
                continue

            font = getattr(run, "font", None)
            piece = MarkdownUtils.apply_emphasis(
                text,
                bold=bool(getattr(font, "bold", False)),
                italic=bool(getattr(font, "italic", False)),
            )

            address = ""
            try:
                address = MarkdownUtils.value_to_text(run.hyperlink.address or "")
            except Exception:
                address = ""

            stripped = piece.strip()
            if address and stripped:
                piece = f"[{stripped}]({address})"
            parts.append(piece)

        return "".join(parts)

    @staticmethod
    def _list_prefix_for_paragraph(paragraph: object) -> str:
        try:
            paragraph_properties = paragraph._p.pPr  # type: ignore[attr-defined]
        except Exception:
            paragraph_properties = None

        if paragraph_properties is not None:
            for child in paragraph_properties:
                tag_name = child.tag.rsplit("}", 1)[-1]
                if tag_name == "buAutoNum":
                    return "1. "
                if tag_name in {"buChar", "buBlip"}:
                    return "- "
                if tag_name == "buNone":
                    return ""

        try:
            level = int(paragraph.level)
        except Exception:
            level = 0

        if level > 0:
            return f"{'  ' * min(level, 4)}- "

        return ""

    def _pptx_table_to_markdown(self, table: object) -> str:
        rows: list[list[str]] = []
        for row in table.rows:
            values = [MarkdownUtils.value_to_text(cell.text) for cell in row.cells]
            if any(value.strip() for value in values):
                rows.append(values)

        return MarkdownUtils.rows_to_markdown_table(rows)

    @staticmethod
    def _shape_image(shape: object, asset_writer: AssetWriter) -> str:
        """Export a picture shape's image and return a Markdown reference."""
        try:
            if not getattr(shape, "shape_type", None):
                return ""
            shape_type_name = getattr(shape.shape_type, "name", "")
            if shape_type_name != "PICTURE" and not hasattr(shape, "image"):
                return ""
            image = shape.image
        except Exception:
            return ""

        data = getattr(image, "blob", None)
        extension = normalize_extension(getattr(image, "ext", "") or "")
        relative_path = asset_writer.save_image(data, extension)
        return image_markdown(relative_path) if relative_path else ""
