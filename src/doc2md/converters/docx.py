"""Word DOCX to Markdown converter."""

from __future__ import annotations

import importlib
import re
from pathlib import Path

from ..markdown_utils import MarkdownUtils
from ..models import DOCX_DEPENDENCY
from .assets import AssetWriter, extension_from_content_type, image_markdown
from .base import DocumentToMarkdownConverter


class DocxMarkdownConverter(DocumentToMarkdownConverter):
    dependency = DOCX_DEPENDENCY
    source_type = "Word DOCX"

    def extract(
        self,
        input_path: Path,
        asset_writer: AssetWriter | None = None,
    ) -> tuple[str, dict[str, str], str]:
        document_module = importlib.import_module("docx")
        paragraph_module = importlib.import_module("docx.text.paragraph")
        table_module = importlib.import_module("docx.table")

        document = document_module.Document(str(input_path))
        paragraph_class = paragraph_module.Paragraph
        table_class = table_module.Table

        core_properties = document.core_properties
        title = MarkdownUtils.value_to_text(core_properties.title) or MarkdownUtils.prettify_title(
            input_path.stem
        )

        extra_metadata: dict[str, str] = {}
        if self.options.include_metadata:
            extra_metadata["Author"] = MarkdownUtils.value_to_text(core_properties.author)
            extra_metadata["Subject"] = MarkdownUtils.value_to_text(core_properties.subject)
            extra_metadata["Title"] = MarkdownUtils.value_to_text(core_properties.title)
            extra_metadata["Comments"] = MarkdownUtils.value_to_text(core_properties.comments)
            extra_metadata["Last modified by"] = MarkdownUtils.value_to_text(core_properties.last_modified_by)
            extra_metadata["Created"] = MarkdownUtils.value_to_text(core_properties.created)
            extra_metadata["Modified"] = MarkdownUtils.value_to_text(core_properties.modified)

        blocks: list[str] = []
        for child in document.element.body.iterchildren():
            tag = child.tag.rsplit("}", 1)[-1]
            if tag == "p":
                paragraph = paragraph_class(child, document)
                markdown_paragraph = self._paragraph_to_markdown(paragraph)
                if markdown_paragraph:
                    blocks.append(markdown_paragraph)
                if asset_writer is not None:
                    blocks.extend(self._paragraph_images(paragraph, document, asset_writer))
            elif tag == "tbl":
                table = table_class(child, document)
                markdown_table = self._table_to_markdown(table)
                if markdown_table:
                    blocks.append(markdown_table)

        content = "\n\n".join(block for block in blocks if block.strip())
        if not content:
            content = "_No extractable text was found in this Word document._"

        return title, extra_metadata, content

    @staticmethod
    def _paragraph_images(paragraph: object, document: object, asset_writer: AssetWriter) -> list[str]:
        """Export images embedded in a paragraph and return Markdown references."""
        from docx.oxml.ns import qn

        refs: list[str] = []
        try:
            blips = paragraph._p.findall(".//" + qn("a:blip"))  # type: ignore[attr-defined]
        except Exception:
            return refs

        related_parts = getattr(document.part, "related_parts", {})
        for blip in blips:
            rel_id = blip.get(qn("r:embed")) or blip.get(qn("r:link"))
            if not rel_id or rel_id not in related_parts:
                continue
            part = related_parts[rel_id]
            data = getattr(part, "blob", None)
            extension = extension_from_content_type(getattr(part, "content_type", ""))
            relative_path = asset_writer.save_image(data, extension)
            if relative_path:
                refs.append(image_markdown(relative_path))
        return refs

    def _paragraph_to_markdown(self, paragraph: object) -> str:
        text = MarkdownUtils.value_to_text(getattr(paragraph, "text", ""))
        if self.options.normalize_whitespace or self.options.optimize_for_ai:
            text = MarkdownUtils.value_to_text(MarkdownUtils.normalize_text(text))

        if not text:
            return ""

        inline = self._inline_to_markdown(paragraph)
        if self.options.normalize_whitespace or self.options.optimize_for_ai:
            inline = MarkdownUtils.value_to_text(MarkdownUtils.normalize_text(inline))
        if not inline:
            inline = text

        style_name = ""
        try:
            style_name = MarkdownUtils.value_to_text(paragraph.style.name)
        except Exception:
            style_name = ""

        style_lower = style_name.lower()
        heading_match = re.match(r"heading\s+(\d+)", style_name, re.IGNORECASE)
        if heading_match:
            level = min(6, int(heading_match.group(1)) + 1)
            return f"{'#' * level} {inline}"

        is_numbered = "list number" in style_lower or "number" in style_lower
        is_bulleted = "list bullet" in style_lower or "bullet" in style_lower

        try:
            paragraph_properties = paragraph._p.pPr  # type: ignore[attr-defined]
            if paragraph_properties is not None and paragraph_properties.numPr is not None:
                if is_numbered:
                    return f"1. {inline}"
                if is_bulleted or "list" in style_lower:
                    return f"- {inline}"
        except Exception:
            pass

        if is_numbered:
            return f"1. {inline}"
        if is_bulleted:
            return f"- {inline}"

        return MarkdownUtils.convert_line_to_markdown(inline, self.options)

    def _inline_to_markdown(self, paragraph: object) -> str:
        """Render a paragraph's runs and hyperlinks, preserving bold, italic, and links."""
        try:
            inner_items = list(paragraph.iter_inner_content())
        except Exception:
            inner_items = None

        if inner_items is not None:
            parts: list[str] = []
            for item in inner_items:
                if hasattr(item, "runs"):  # Hyperlink
                    parts.append(self._hyperlink_to_markdown(item))
                else:  # Run
                    parts.append(self._run_to_markdown(item))
            return "".join(parts)

        return "".join(self._run_to_markdown(run) for run in getattr(paragraph, "runs", []))

    def _hyperlink_to_markdown(self, hyperlink: object) -> str:
        link_text = "".join(self._run_to_markdown(run) for run in getattr(hyperlink, "runs", []))
        address = MarkdownUtils.value_to_text(getattr(hyperlink, "address", "") or "")
        stripped = link_text.strip()
        if address and stripped:
            return f"[{stripped}]({address})"
        return link_text

    @staticmethod
    def _run_to_markdown(run: object) -> str:
        text = getattr(run, "text", "") or ""
        if not text:
            return ""
        return MarkdownUtils.apply_emphasis(
            text,
            bold=bool(getattr(run, "bold", False)),
            italic=bool(getattr(run, "italic", False)),
        )

    def _table_to_markdown(self, table: object) -> str:
        rows: list[list[str]] = []
        for row in getattr(table, "rows", []):
            values: list[str] = []
            for cell in row.cells:
                cell_text = " ".join(
                    MarkdownUtils.value_to_text(self._inline_to_markdown(paragraph))
                    for paragraph in getattr(cell, "paragraphs", [])
                    if MarkdownUtils.value_to_text(paragraph.text)
                )
                values.append(cell_text)
            if any(value.strip() for value in values):
                rows.append(values)

        return MarkdownUtils.rows_to_markdown_table(rows)
