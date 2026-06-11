"""Word DOCX to Markdown converter."""

from __future__ import annotations

import importlib
import re
from pathlib import Path

from ..markdown_utils import MarkdownUtils
from ..models import DOCX_DEPENDENCY
from .assets import AssetWriter, extension_from_content_type, image_markdown
from .base import DocumentToMarkdownConverter
from .comments import (
    ANCHOR_CLOSE,
    ANCHOR_OPEN,
    Comment,
    render_comment_callout,
    superscript,
)


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

        self._reset_comment_state()
        if self.options.include_comments:
            try:
                self._load_comments(document)
            except Exception:
                self._reset_comment_state()

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
                blocks.extend(self._flush_comment_callouts())
            elif tag == "tbl":
                table = table_class(child, document)
                markdown_table = self._table_to_markdown(table)
                if markdown_table:
                    blocks.append(markdown_table)
                blocks.extend(self._flush_comment_callouts())

        blocks.extend(self._unanchored_comment_callouts())

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

        inline = self._inline_for(paragraph)
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
                    MarkdownUtils.value_to_text(self._inline_for(paragraph))
                    for paragraph in getattr(cell, "paragraphs", [])
                    if MarkdownUtils.value_to_text(paragraph.text)
                )
                values.append(cell_text)
            if any(value.strip() for value in values):
                rows.append(values)

        return MarkdownUtils.rows_to_markdown_table(rows)

    # -- Review comments -------------------------------------------------------

    def _reset_comment_state(self) -> None:
        self._comments_by_id: dict[str, Comment] = {}
        self._top_level_ids: set[str] = set()
        self._open_comment_ids: list[str] = []
        self._closed_comment_ids: list[str] = []
        self._anchor_acc: dict[str, str] = {}
        self._comment_index_counter = 0
        self._emitted_comment_ids: set[str] = set()

    def _comment_anchoring_enabled(self) -> bool:
        return self.options.include_comments and bool(self._top_level_ids)

    def _inline_for(self, paragraph: object) -> str:
        if self._comment_anchoring_enabled():
            return self._inline_to_markdown_comment_aware(paragraph)
        return self._inline_to_markdown(paragraph)

    def _inline_to_markdown_comment_aware(self, paragraph: object) -> str:
        """Render a paragraph's runs while wrapping commented spans with anchor markers."""
        from docx.oxml.ns import qn
        from docx.text.hyperlink import Hyperlink
        from docx.text.run import Run

        parts: list[str] = []
        for child in paragraph._p.iterchildren():  # type: ignore[attr-defined]
            tag = child.tag.rsplit("}", 1)[-1]
            if tag == "commentRangeStart":
                comment_id = child.get(qn("w:id"))
                if comment_id in self._top_level_ids and comment_id not in self._open_comment_ids:
                    self._open_comment_ids.append(comment_id)
                    self._anchor_acc.setdefault(comment_id, "")
                    parts.append(ANCHOR_OPEN)
            elif tag == "commentRangeEnd":
                comment_id = child.get(qn("w:id"))
                if comment_id in self._open_comment_ids:
                    comment = self._comments_by_id.get(comment_id)
                    if comment is not None:
                        comment.anchor_text = self._anchor_acc.get(comment_id, "")
                    index = self._assign_comment_index(comment_id)
                    parts.append(ANCHOR_CLOSE + superscript(index))
                    self._open_comment_ids.remove(comment_id)
                    self._closed_comment_ids.append(comment_id)
            elif tag == "r":
                run = Run(child, paragraph)
                parts.append(self._run_to_markdown(run))
                self._accumulate_anchor(getattr(run, "text", "") or "")
            elif tag == "hyperlink":
                link = Hyperlink(child, paragraph)
                parts.append(self._hyperlink_to_markdown(link))
                link_text = "".join(getattr(run, "text", "") or "" for run in getattr(link, "runs", []))
                self._accumulate_anchor(link_text)
        return "".join(parts)

    def _accumulate_anchor(self, text: str) -> None:
        if not text or not self._open_comment_ids:
            return
        for comment_id in self._open_comment_ids:
            self._anchor_acc[comment_id] = self._anchor_acc.get(comment_id, "") + text

    def _assign_comment_index(self, comment_id: str) -> int:
        comment = self._comments_by_id.get(comment_id)
        if comment is None:
            return 0
        if comment.index == 0:
            self._comment_index_counter += 1
            comment.index = self._comment_index_counter
        return comment.index

    def _take_closed_comment_ids(self) -> list[str]:
        closed = self._closed_comment_ids
        self._closed_comment_ids = []
        return closed

    def _flush_comment_callouts(self) -> list[str]:
        callouts: list[str] = []
        for comment_id in self._take_closed_comment_ids():
            comment = self._comments_by_id.get(comment_id)
            if comment is None or comment_id in self._emitted_comment_ids:
                continue
            self._emitted_comment_ids.add(comment_id)
            callouts.append(render_comment_callout(comment))
        return callouts

    def _unanchored_comment_callouts(self) -> list[str]:
        if not self.options.include_comments:
            return []
        leftover_ids = [
            comment_id for comment_id in self._top_level_ids if comment_id not in self._emitted_comment_ids
        ]
        if not leftover_ids:
            return []
        leftover_ids.sort(key=self._comment_sort_key)
        callouts: list[str] = []
        for comment_id in leftover_ids:
            comment = self._comments_by_id.get(comment_id)
            if comment is None:
                continue
            self._assign_comment_index(comment_id)
            self._emitted_comment_ids.add(comment_id)
            callouts.append(render_comment_callout(comment))
        return ["### Unanchored comments", *callouts]

    @staticmethod
    def _comment_sort_key(comment_id: str) -> tuple[int, object]:
        return (0, int(comment_id)) if comment_id.isdigit() else (1, comment_id)

    def _load_comments(self, document: object) -> None:
        """Parse comments.xml (and commentsExtended.xml) into the converter's state."""
        from docx.oxml.ns import qn
        from lxml import etree

        word_2010 = "http://schemas.microsoft.com/office/word/2010/wordml"
        word_2012 = "http://schemas.microsoft.com/office/word/2012/wordml"

        comments_blob, comments_ex_blob = self._read_comment_parts(document)
        if not comments_blob:
            return

        root = etree.fromstring(comments_blob)
        paraid_to_id: dict[str, str] = {}
        for comment_el in root.findall(qn("w:comment")):
            comment_id = comment_el.get(qn("w:id"))
            if comment_id is None:
                continue
            comment = Comment(
                author=(comment_el.get(qn("w:author")) or "").strip(),
                date=self._format_comment_date(comment_el.get(qn("w:date")) or ""),
                text=self._comment_element_text(comment_el, qn),
            )
            self._comments_by_id[comment_id] = comment
            for paragraph_el in comment_el.findall(qn("w:p")):
                para_id = paragraph_el.get(f"{{{word_2010}}}paraId")
                if para_id:
                    paraid_to_id[para_id] = comment_id

        reply_ids = self._apply_comments_extended(comments_ex_blob, paraid_to_id, word_2012)
        self._top_level_ids = {
            comment_id for comment_id in self._comments_by_id if comment_id not in reply_ids
        }

    def _apply_comments_extended(
        self,
        comments_ex_blob: bytes | None,
        paraid_to_id: dict[str, str],
        word_2012: str,
    ) -> set[str]:
        """Apply resolved status and threading; return the set of reply comment ids."""
        reply_ids: set[str] = set()
        if not comments_ex_blob:
            return reply_ids

        from lxml import etree

        try:
            ex_root = etree.fromstring(comments_ex_blob)
        except Exception:
            return reply_ids

        for ex_el in ex_root.findall(f"{{{word_2012}}}commentEx"):
            comment_id = paraid_to_id.get(ex_el.get(f"{{{word_2012}}}paraId") or "")
            if comment_id is None:
                continue
            comment = self._comments_by_id.get(comment_id)
            if comment is None:
                continue
            if (ex_el.get(f"{{{word_2012}}}done") or "") in ("1", "true", "True"):
                comment.resolved = True
            parent_id = paraid_to_id.get(ex_el.get(f"{{{word_2012}}}paraIdParent") or "")
            if parent_id and parent_id != comment_id:
                parent = self._comments_by_id.get(parent_id)
                if parent is not None:
                    parent.replies.append(comment)
                    reply_ids.add(comment_id)
        return reply_ids

    @staticmethod
    def _read_comment_parts(document: object) -> tuple[bytes | None, bytes | None]:
        comments_blob: bytes | None = None
        comments_ex_blob: bytes | None = None
        try:
            parts = document.part.package.iter_parts()
        except Exception:
            return None, None
        for part in parts:
            try:
                partname = str(getattr(part, "partname", ""))
                blob = getattr(part, "blob", None)
            except Exception:
                continue
            if blob is None:
                continue
            if partname.endswith("/comments.xml"):
                comments_blob = blob
            elif partname.endswith("/commentsExtended.xml"):
                comments_ex_blob = blob
        return comments_blob, comments_ex_blob

    @staticmethod
    def _comment_element_text(comment_el: object, qn: object) -> str:
        paragraph_texts: list[str] = []
        for paragraph_el in comment_el.findall(qn("w:p")):  # type: ignore[operator]
            runs_text = "".join(node.text or "" for node in paragraph_el.iter(qn("w:t")))  # type: ignore[operator]
            if runs_text.strip():
                paragraph_texts.append(runs_text.strip())
        return "\n".join(paragraph_texts).strip()

    @staticmethod
    def _format_comment_date(value: str) -> str:
        value = (value or "").strip()
        if not value:
            return ""
        match = re.match(r"(\d{4})-(\d{2})-(\d{2})(?:T(\d{2}):(\d{2}))?", value)
        if not match:
            return value
        year, month, day, hour, minute = match.groups()
        if hour and minute:
            return f"{year}-{month}-{day} {hour}:{minute}"
        return f"{year}-{month}-{day}"
