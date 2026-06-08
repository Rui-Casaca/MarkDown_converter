"""Shared Markdown cleanup and formatting helpers."""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path

from .models import ConversionOptions


class MarkdownUtils:
    """Shared Markdown cleanup and formatting helpers."""

    @staticmethod
    def normalize_text(text: str) -> str:
        working_text = text.replace("\r\n", "\n").replace("\r", "\n")
        working_text = working_text.replace("\t", " ")
        working_text = re.sub(r"(\w)-\n(\w)", r"\1\2", working_text)

        normalized_lines: list[str] = []
        for line in working_text.split("\n"):
            normalized_lines.append(re.sub(r"[ \t]+", " ", line).strip())

        return "\n".join(normalized_lines)

    @staticmethod
    def remove_repeated_empty_lines(lines: list[str]) -> list[str]:
        cleaned: list[str] = []
        empty_seen = False

        for line in lines:
            if line.strip():
                cleaned.append(line)
                empty_seen = False
            elif not empty_seen:
                cleaned.append("")
                empty_seen = True

        while cleaned and not cleaned[0].strip():
            cleaned.pop(0)
        while cleaned and not cleaned[-1].strip():
            cleaned.pop()

        return cleaned

    @staticmethod
    def looks_like_heading(line: str) -> bool:
        text = line.strip()
        if not text or len(text) > 90:
            return False
        if len(text.split()) > 12:
            return False
        if text.endswith((".", ",", ";", ":")) and not re.match(r"^\d+(?:\.\d+)*[\.)]?\s+", text):
            return False
        if re.match(r"^(chapter|section|part|appendix)\s+\w+", text, re.IGNORECASE):
            return True

        numbered_heading = re.match(r"^\d+(?:\.\d+)*[\.)]?\s+(.+)$", text)
        if numbered_heading:
            remainder = numbered_heading.group(1).strip()
            return bool(remainder) and len(remainder.split()) <= 10

        letters_only = re.sub(r"[^A-Za-zÀ-ÖØ-öø-ÿ]", "", text)
        if len(letters_only) >= 4 and letters_only.upper() == letters_only and len(text.split()) <= 8:
            return True

        words = re.findall(r"[A-Za-zÀ-ÖØ-öø-ÿ0-9]+", text)
        if 2 <= len(words) <= 10:
            capitalized_words = sum(1 for word in words if word[:1].isupper())
            return capitalized_words / len(words) >= 0.8

        return False

    @staticmethod
    def guess_heading_level(line: str) -> int:
        text = line.strip()
        numbered_heading = re.match(r"^(\d+(?:\.(\d+))*)", text)
        if numbered_heading:
            depth = numbered_heading.group(1).count(".") + 1
            return min(6, 2 + depth)
        return 3

    @staticmethod
    def convert_line_to_markdown(line: str, options: ConversionOptions) -> str:
        text = line.strip()
        if not text:
            return ""

        if re.match(r"^[•●▪▫◦‣]\s*", text):
            text = re.sub(r"^[•●▪▫◦‣]\s*", "- ", text)
        elif re.match(r"^[-–—]\s+", text):
            text = re.sub(r"^[-–—]\s+", "- ", text)

        numbered_match = re.match(r"^(\d+)[\)]\s+(.+)$", text)
        if numbered_match:
            text = f"{numbered_match.group(1)}. {numbered_match.group(2)}"

        if options.detect_headings and MarkdownUtils.looks_like_heading(text):
            clean_heading = text.strip(" .")
            return f"{'#' * MarkdownUtils.guess_heading_level(clean_heading)} {clean_heading}"

        return text

    @staticmethod
    def apply_emphasis(text: str, *, bold: bool = False, italic: bool = False) -> str:
        """Wrap ``text`` in Markdown emphasis markers, keeping outer whitespace outside."""
        if not text or not text.strip() or not (bold or italic):
            return text

        leading = text[: len(text) - len(text.lstrip())]
        trailing = text[len(text.rstrip()) :]
        core = text.strip()

        if bold and italic:
            marker = "***"
        elif bold:
            marker = "**"
        else:
            marker = "*"

        return f"{leading}{marker}{core}{marker}{trailing}"

    @staticmethod
    def sanitize_markdown(markdown: str) -> str:
        lines = [line.rstrip() for line in markdown.replace("\r\n", "\n").replace("\r", "\n").split("\n")]
        cleaned = MarkdownUtils.remove_repeated_empty_lines(lines)
        return "\n".join(cleaned)

    @staticmethod
    def slugify_heading(heading: str) -> str:
        slug = re.sub(r"[^\w\s-]", "", heading.lower()).strip()
        slug = re.sub(r"[\s_-]+", "-", slug)
        slug = re.sub(r"-+", "-", slug)
        return slug or "section"

    @staticmethod
    def generate_table_of_contents(markdown: str) -> str:
        toc_lines: list[str] = []
        slug_counts: dict[str, int] = {}

        for line in markdown.splitlines():
            match = re.match(r"^(#{2,6})\s+(.+)$", line.strip())
            if not match:
                continue

            heading = match.group(2).strip()
            if not heading:
                continue

            level = len(match.group(1)) - 2
            slug = MarkdownUtils.slugify_heading(heading)
            if slug in slug_counts:
                slug_counts[slug] += 1
                anchor = f"{slug}-{slug_counts[slug]}"
            else:
                slug_counts[slug] = 0
                anchor = slug

            toc_lines.append(f"{'  ' * max(level, 0)}- [{heading}](#{anchor})")

        if not toc_lines:
            return "_No structured table of contents could be generated automatically._"

        return "\n".join(toc_lines)

    @staticmethod
    def unique_output_path(path: Path) -> Path:
        if not path.exists():
            return path

        index = 1
        while True:
            candidate = path.with_name(f"{path.stem}_{index}{path.suffix}")
            if not candidate.exists():
                return candidate
            index += 1

    @staticmethod
    def prettify_title(value: str) -> str:
        cleaned = value.replace("_", " ").replace("-", " ")
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        return cleaned or "Untitled Document"

    @staticmethod
    def value_to_text(value: object) -> str:
        if value is None:
            return ""
        if isinstance(value, datetime):
            return value.strftime("%Y-%m-%d %H:%M")
        return re.sub(r"\s+", " ", str(value).strip())

    @staticmethod
    def rows_to_markdown_table(rows: list[list[str]]) -> str:
        if not rows:
            return ""

        width = max(len(row) for row in rows)
        normalized_rows: list[list[str]] = []

        for row in rows:
            padded = row + [""] * (width - len(row))
            normalized_cells = []
            for cell in padded:
                cell_text = MarkdownUtils.value_to_text(cell).replace("|", "\\|")
                normalized_cells.append(cell_text)
            normalized_rows.append(normalized_cells)

        header = normalized_rows[0]
        separator = ["---"] * width
        body = normalized_rows[1:]
        table_lines = [
            f"| {' | '.join(header)} |",
            f"| {' | '.join(separator)} |",
        ]
        table_lines.extend(f"| {' | '.join(row)} |" for row in body)
        return "\n".join(table_lines)

    @staticmethod
    def text_to_markdown(text: str, options: ConversionOptions) -> str:
        if not text or not text.strip():
            return ""

        working_text = text
        if options.normalize_whitespace or options.optimize_for_ai:
            working_text = MarkdownUtils.normalize_text(text)
        else:
            working_text = text.replace("\r\n", "\n").replace("\r", "\n")

        raw_lines = [line.strip() for line in working_text.split("\n")]
        raw_lines = MarkdownUtils.remove_repeated_empty_lines(raw_lines)

        markdown_lines: list[str] = []
        paragraph_parts: list[str] = []

        def flush_paragraph() -> None:
            if paragraph_parts:
                markdown_lines.append(" ".join(paragraph_parts).strip())
                paragraph_parts.clear()

        for raw_line in raw_lines:
            if not raw_line:
                flush_paragraph()
                if markdown_lines and markdown_lines[-1] != "":
                    markdown_lines.append("")
                continue

            converted_line = MarkdownUtils.convert_line_to_markdown(raw_line, options)
            is_block = bool(
                re.match(r"^(#{2,6})\s+", converted_line)
                or re.match(r"^-\s+", converted_line)
                or re.match(r"^\d+\.\s+", converted_line)
                or converted_line.startswith("<!--")
                or converted_line == "---"
                or converted_line.startswith("|")
            )

            if is_block:
                flush_paragraph()
                markdown_lines.append(converted_line)
                continue

            paragraph_parts.append(converted_line)

        flush_paragraph()
        cleaned_lines = MarkdownUtils.remove_repeated_empty_lines(markdown_lines)
        return "\n".join(cleaned_lines)
