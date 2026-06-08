#!/usr/bin/env python3
"""Standalone Windows-focused GUI for converting documents to Markdown."""

from __future__ import annotations

import importlib
import importlib.util
import re
import subprocess
import sys
import tempfile
import threading
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Callable, Iterable, Optional

import tkinter as tk
from tkinter import filedialog, messagebox, ttk


APP_TITLE = "Document to Markdown Converter"
OUTPUT_FOLDER_NAME = "MarkDowns_converted"
SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".pptx"}
MODE_SINGLE = "Single file"
MODE_MULTIPLE = "Multiple files"
MODE_FOLDER = "Folder"
MANUAL_INSTALL_COMMAND = "python -m pip install pypdf python-docx python-pptx"
FILE_DIALOG_TYPES = [
    ("Supported documents", "*.pdf *.docx *.pptx"),
    ("PDF files", "*.pdf"),
    ("Word documents", "*.docx"),
    ("PowerPoint presentations", "*.pptx"),
    ("All files", "*.*"),
]
SOURCE_TYPE_BY_EXTENSION = {
    ".pdf": "PDF",
    ".docx": "Word DOCX",
    ".pptx": "PowerPoint PPTX",
}


@dataclass(frozen=True)
class Dependency:
    display_name: str
    import_name: str
    package_name: str
    required_for: str


@dataclass
class ConversionOptions:
    include_metadata: bool = True
    include_page_slide_separators: bool = True
    detect_headings: bool = True
    normalize_whitespace: bool = True
    optimize_for_ai: bool = True
    include_subfolders: bool = False
    overwrite_existing: bool = True
    enabled_extensions: set[str] = field(default_factory=lambda: set(SUPPORTED_EXTENSIONS))


@dataclass(frozen=True)
class ConversionJob:
    input_path: Path
    output_path: Path
    source_type: str


@dataclass(frozen=True)
class ConversionResult:
    input_path: Path
    output_path: Path
    success: bool
    message: str


class DependencyManager:
    """Checks and optionally installs pip dependencies without blocking the GUI."""

    def __init__(self, dependencies: list[Dependency]) -> None:
        self.dependencies = dependencies

    def is_installed(self, dependency: Dependency) -> bool:
        return importlib.util.find_spec(dependency.import_name) is not None

    def get_missing_dependencies(self) -> list[Dependency]:
        return [dependency for dependency in self.dependencies if not self.is_installed(dependency)]

    def get_status_lines(self) -> list[str]:
        lines: list[str] = []
        for dependency in self.dependencies:
            state = "installed" if self.is_installed(dependency) else "missing"
            lines.append(
                f"Dependency status: {dependency.display_name} is {state} "
                f"({dependency.required_for})."
            )
        return lines

    @staticmethod
    def format_dependency_list(dependencies: Iterable[Dependency]) -> str:
        return "\n".join(
            f"- {dependency.display_name} ({dependency.package_name}) for {dependency.required_for}"
            for dependency in dependencies
        )

    def install_missing_dependencies(
        self,
        dependencies: Iterable[Dependency],
        log_callback: Callable[[str], None],
    ) -> tuple[bool, str, list[Dependency]]:
        failures: list[str] = []

        for dependency in dependencies:
            command = [sys.executable, "-m", "pip", "install", dependency.package_name]
            log_callback(
                f"Installing dependency: {dependency.display_name} with command: "
                f"{' '.join(command)}"
            )

            with tempfile.NamedTemporaryFile("w", delete=False, encoding="utf-8", suffix=".log") as temp_file:
                temp_log_path = Path(temp_file.name)

            try:
                with temp_log_path.open("w", encoding="utf-8", errors="replace") as handle:
                    subprocess.check_call(command, stdout=handle, stderr=handle)
                log_callback(f"Dependency installed successfully: {dependency.display_name}")
            except subprocess.CalledProcessError as exc:
                details = temp_log_path.read_text(encoding="utf-8", errors="replace").strip()
                failure_message = self._build_install_failure_message(
                    dependency=dependency,
                    return_code=exc.returncode,
                    details=details,
                )
                failures.append(failure_message)
                log_callback(failure_message)
            except Exception as exc:
                failure_message = (
                    f"Unexpected error while installing {dependency.display_name}: {exc}\n"
                    f"You can install dependencies manually with:\n{MANUAL_INSTALL_COMMAND}"
                )
                failures.append(failure_message)
                log_callback(failure_message)
            finally:
                try:
                    temp_log_path.unlink(missing_ok=True)
                except OSError:
                    pass

        remaining_missing = self.get_missing_dependencies()
        if remaining_missing:
            message = (
                "Dependency installation finished with missing packages still present.\n"
                f"Remaining missing dependencies:\n{self.format_dependency_list(remaining_missing)}\n\n"
                f"Manual installation command:\n{MANUAL_INSTALL_COMMAND}"
            )
            if failures:
                message = f"{message}\n\nDetailed failures were written to the log."
            return False, message, remaining_missing

        return True, "All requested dependencies are installed and ready to use.", []

    @staticmethod
    def _build_install_failure_message(dependency: Dependency, return_code: int, details: str) -> str:
        lines = [
            f"Failed to install {dependency.display_name} ({dependency.package_name}).",
            f"pip exited with code {return_code}.",
        ]

        lower_details = details.lower()
        if "permission denied" in lower_details or "access is denied" in lower_details:
            lines.append(
                "Permission-related failure detected. Try running inside a virtual environment, "
                "or install manually with:"
            )
            lines.append(MANUAL_INSTALL_COMMAND)
        else:
            lines.append("You can install dependencies manually with:")
            lines.append(MANUAL_INSTALL_COMMAND)

        if details:
            lines.append("pip details:")
            lines.append(details)

        return "\n".join(lines)


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


def build_output_path(
    source_path: Path,
    mode: str,
    overwrite_existing: bool,
    selected_folder: Optional[Path] = None,
    explicit_output_path: Optional[Path] = None,
) -> Path:
    if mode == MODE_SINGLE:
        if explicit_output_path is None:
            raise ValueError("A single-file output path is required.")
        output_path = explicit_output_path
    elif mode == MODE_MULTIPLE:
        output_path = source_path.parent / OUTPUT_FOLDER_NAME / source_path.with_suffix(".md").name
    elif mode == MODE_FOLDER:
        if selected_folder is None:
            raise ValueError("A selected folder is required for folder mode.")
        relative_path = source_path.relative_to(selected_folder)
        output_path = selected_folder / OUTPUT_FOLDER_NAME / relative_path.with_suffix(".md")
    else:
        raise ValueError(f"Unsupported mode: {mode}")

    if output_path.suffix.lower() != ".md":
        output_path = output_path.with_suffix(".md")

    if not overwrite_existing:
        output_path = MarkdownUtils.unique_output_path(output_path)

    return output_path


PDF_DEPENDENCY = Dependency(
    display_name="pypdf",
    import_name="pypdf",
    package_name="pypdf",
    required_for="PDF conversion",
)
DOCX_DEPENDENCY = Dependency(
    display_name="python-docx",
    import_name="docx",
    package_name="python-docx",
    required_for="Word DOCX conversion",
)
PPTX_DEPENDENCY = Dependency(
    display_name="python-pptx",
    import_name="pptx",
    package_name="python-pptx",
    required_for="PowerPoint PPTX conversion",
)


class DocumentToMarkdownConverter:
    """Base class for document converters."""

    dependency: Dependency
    source_type: str

    def __init__(self, options: ConversionOptions, dependency_manager: DependencyManager) -> None:
        self.options = options
        self.dependency_manager = dependency_manager

    def convert(self, job: ConversionJob) -> ConversionResult:
        try:
            if not job.input_path.exists():
                raise FileNotFoundError(f"Input file does not exist: {job.input_path}")

            if not self.dependency_manager.is_installed(self.dependency):
                raise RuntimeError(self._missing_dependency_message())

            title, metadata, content = self.extract(job.input_path)

            output_path = job.output_path
            if output_path.exists() and not self.options.overwrite_existing:
                output_path = MarkdownUtils.unique_output_path(output_path)

            output_path.parent.mkdir(parents=True, exist_ok=True)
            markdown = self._compose_markdown(
                input_path=job.input_path,
                title=title,
                metadata=metadata,
                content=content,
            )
            output_path.write_text(markdown, encoding="utf-8")
            return ConversionResult(job.input_path, output_path, True, "Converted successfully.")
        except PermissionError as exc:
            return ConversionResult(
                job.input_path,
                job.output_path,
                False,
                f"Permission error while writing the Markdown file: {exc}",
            )
        except Exception as exc:
            return ConversionResult(job.input_path, job.output_path, False, str(exc))

    def extract(self, input_path: Path) -> tuple[str, dict[str, str], str]:
        raise NotImplementedError

    def _compose_markdown(
        self,
        input_path: Path,
        title: str,
        metadata: dict[str, str],
        content: str,
    ) -> str:
        safe_title = title.strip() or MarkdownUtils.prettify_title(input_path.stem)
        content_body = content.strip() or "_No extractable text was found in this document._"
        toc = MarkdownUtils.generate_table_of_contents(content_body)

        lines = [
            f"# {safe_title}",
            "",
            "> Converted to Markdown.",
            f"> Source file: `{input_path.name}`",
            f"> Source type: {self.source_type}",
            f"> Conversion date: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            f"> AI-readable format: {'enabled' if self.options.optimize_for_ai else 'disabled'}",
        ]

        if self.options.include_metadata:
            for key, value in metadata.items():
                if value:
                    lines.append(f"> {key}: {value}")

        lines.extend(
            [
                "",
                "## Table of Contents",
                "",
                toc,
                "",
                "## Content",
                "",
                content_body,
                "",
                "---",
                "",
                "_Conversion completed by Document to Markdown Converter._",
            ]
        )

        markdown = "\n".join(lines)
        return MarkdownUtils.sanitize_markdown(markdown).rstrip() + "\n"

    def _missing_dependency_message(self) -> str:
        return (
            f"Missing dependency for {self.source_type} conversion: {self.dependency.display_name}.\n"
            f"Install it with:\n{MANUAL_INSTALL_COMMAND}"
        )


class PdfMarkdownConverter(DocumentToMarkdownConverter):
    dependency = PDF_DEPENDENCY
    source_type = "PDF"

    def extract(self, input_path: Path) -> tuple[str, dict[str, str], str]:
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
        page_blocks: list[str] = []

        for index, page in enumerate(reader.pages, start=1):
            if self.options.include_page_slide_separators:
                if page_blocks:
                    page_blocks.append("")
                page_blocks.extend(["---", f"<!-- Page {index} -->", ""])

            try:
                raw_text = page.extract_text() or ""
            except Exception:
                raw_text = ""

            page_markdown = MarkdownUtils.text_to_markdown(raw_text, self.options)
            if page_markdown:
                page_blocks.append(page_markdown)
            else:
                page_blocks.append("_No selectable text was found on this page. OCR may be required._")

        content = "\n\n".join(block for block in page_blocks if block.strip())
        if not content:
            content = "_No selectable text was extracted from this PDF. OCR may be required._"

        return title, extra_metadata, content

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


class DocxMarkdownConverter(DocumentToMarkdownConverter):
    dependency = DOCX_DEPENDENCY
    source_type = "Word DOCX"

    def extract(self, input_path: Path) -> tuple[str, dict[str, str], str]:
        document_module = importlib.import_module("docx")
        paragraph_module = importlib.import_module("docx.text.paragraph")
        table_module = importlib.import_module("docx.table")

        document = document_module.Document(str(input_path))
        paragraph_class = paragraph_module.Paragraph
        table_class = table_module.Table

        core_properties = document.core_properties
        title = MarkdownUtils.value_to_text(core_properties.title) or MarkdownUtils.prettify_title(input_path.stem)

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
            elif tag == "tbl":
                table = table_class(child, document)
                markdown_table = self._table_to_markdown(table)
                if markdown_table:
                    blocks.append(markdown_table)

        content = "\n\n".join(block for block in blocks if block.strip())
        if not content:
            content = "_No extractable text was found in this Word document._"

        return title, extra_metadata, content

    def _paragraph_to_markdown(self, paragraph: object) -> str:
        text = MarkdownUtils.value_to_text(getattr(paragraph, "text", ""))
        if self.options.normalize_whitespace or self.options.optimize_for_ai:
            text = MarkdownUtils.value_to_text(MarkdownUtils.normalize_text(text))

        if not text:
            return ""

        style_name = ""
        try:
            style_name = MarkdownUtils.value_to_text(paragraph.style.name)
        except Exception:
            style_name = ""

        style_lower = style_name.lower()
        heading_match = re.match(r"heading\s+(\d+)", style_name, re.IGNORECASE)
        if heading_match:
            level = min(6, int(heading_match.group(1)) + 1)
            return f"{'#' * level} {text}"

        is_numbered = "list number" in style_lower or "number" in style_lower
        is_bulleted = "list bullet" in style_lower or "bullet" in style_lower

        try:
            paragraph_properties = paragraph._p.pPr  # type: ignore[attr-defined]
            if paragraph_properties is not None and paragraph_properties.numPr is not None:
                if is_numbered:
                    return f"1. {text}"
                if is_bulleted or "list" in style_lower:
                    return f"- {text}"
        except Exception:
            pass

        if is_numbered:
            return f"1. {text}"
        if is_bulleted:
            return f"- {text}"

        return MarkdownUtils.convert_line_to_markdown(text, self.options)

    def _table_to_markdown(self, table: object) -> str:
        rows: list[list[str]] = []
        for row in getattr(table, "rows", []):
            values: list[str] = []
            for cell in row.cells:
                cell_text = " ".join(
                    MarkdownUtils.value_to_text(paragraph.text)
                    for paragraph in getattr(cell, "paragraphs", [])
                    if MarkdownUtils.value_to_text(paragraph.text)
                )
                values.append(cell_text)
            if any(value.strip() for value in values):
                rows.append(values)

        return MarkdownUtils.rows_to_markdown_table(rows)


class PptxMarkdownConverter(DocumentToMarkdownConverter):
    dependency = PPTX_DEPENDENCY
    source_type = "PowerPoint PPTX"

    def extract(self, input_path: Path) -> tuple[str, dict[str, str], str]:
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

                if not getattr(shape, "has_text_frame", False):
                    continue

                text_block_lines: list[str] = []
                for paragraph in shape.text_frame.paragraphs:
                    paragraph_text = MarkdownUtils.value_to_text(paragraph.text)
                    if self.options.normalize_whitespace or self.options.optimize_for_ai:
                        paragraph_text = MarkdownUtils.value_to_text(MarkdownUtils.normalize_text(paragraph_text))

                    if not paragraph_text:
                        continue
                    if title_shape_id is None and fallback_title and paragraph_text == fallback_title and not used_fallback_title:
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

    def _extract_slide_title(self, slide: object) -> tuple[str, Optional[int], Optional[str]]:
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
        list_prefix = self._list_prefix_for_paragraph(paragraph)
        if list_prefix:
            return f"{list_prefix}{paragraph_text}"
        return MarkdownUtils.convert_line_to_markdown(paragraph_text, self.options)

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


def get_converter_for_path(
    path: Path,
    options: ConversionOptions,
    dependency_manager: DependencyManager,
) -> DocumentToMarkdownConverter:
    extension = path.suffix.lower()
    if extension == ".pdf":
        return PdfMarkdownConverter(options, dependency_manager)
    if extension == ".docx":
        return DocxMarkdownConverter(options, dependency_manager)
    if extension == ".pptx":
        return PptxMarkdownConverter(options, dependency_manager)
    raise ValueError(f"Unsupported file type: {path.suffix}")


class DocumentToMarkdownApp(tk.Tk):
    """Tkinter application for converting PDF, DOCX, and PPTX files to Markdown."""

    def __init__(self) -> None:
        super().__init__()
        self.title(APP_TITLE)
        self.geometry("900x650")
        self.minsize(820, 560)

        self.dependencies = [PDF_DEPENDENCY, DOCX_DEPENDENCY, PPTX_DEPENDENCY]
        self.dependency_manager = DependencyManager(self.dependencies)

        self.single_input_path: Optional[Path] = None
        self.multiple_input_paths: list[Path] = []
        self.folder_input_path: Optional[Path] = None
        self.install_running = False
        self.conversion_running = False

        self.input_mode_var = tk.StringVar(value=MODE_SINGLE)
        self.input_summary_var = tk.StringVar()
        self.output_path_var = tk.StringVar()
        self.status_var = tk.StringVar(value="Ready.")

        self.pdf_enabled_var = tk.BooleanVar(value=True)
        self.docx_enabled_var = tk.BooleanVar(value=True)
        self.pptx_enabled_var = tk.BooleanVar(value=True)

        self.include_metadata_var = tk.BooleanVar(value=True)
        self.include_page_slide_separators_var = tk.BooleanVar(value=True)
        self.detect_headings_var = tk.BooleanVar(value=True)
        self.normalize_whitespace_var = tk.BooleanVar(value=True)
        self.optimize_for_ai_var = tk.BooleanVar(value=True)
        self.include_subfolders_var = tk.BooleanVar(value=False)
        self.overwrite_existing_var = tk.BooleanVar(value=True)

        self._build_ui()
        self._handle_mode_change(clear_selection=False)
        self.after(200, self._startup_dependency_check)

    def _build_ui(self) -> None:
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        main = ttk.Frame(self, padding=16)
        main.grid(row=0, column=0, sticky="nsew")
        main.columnconfigure(0, weight=1)
        main.rowconfigure(5, weight=1)

        header_frame = ttk.Frame(main)
        header_frame.grid(row=0, column=0, sticky="ew")
        header_frame.columnconfigure(0, weight=1)

        ttk.Label(header_frame, text=APP_TITLE, font=("TkDefaultFont", 16, "bold")).grid(
            row=0, column=0, sticky="w"
        )
        ttk.Label(
            header_frame,
            text=(
                "Convert PDF, Word DOCX, and PowerPoint PPTX documents into clean Markdown "
                "optimized for AI reading, summarization, embeddings, RAG ingestion, and question answering."
            ),
            wraplength=850,
        ).grid(row=1, column=0, sticky="w", pady=(6, 0))

        input_frame = ttk.LabelFrame(main, text="Input configuration", padding=12)
        input_frame.grid(row=1, column=0, sticky="ew", pady=(14, 10))
        input_frame.columnconfigure(1, weight=1)

        ttk.Label(input_frame, text="Input mode:").grid(row=0, column=0, sticky="w", pady=4)
        self.mode_combo = ttk.Combobox(
            input_frame,
            textvariable=self.input_mode_var,
            values=[MODE_SINGLE, MODE_MULTIPLE, MODE_FOLDER],
            state="readonly",
            width=18,
        )
        self.mode_combo.grid(row=0, column=1, sticky="w", pady=4)
        self.mode_combo.bind("<<ComboboxSelected>>", self._on_mode_changed)

        ttk.Label(input_frame, text="Selected input:").grid(row=1, column=0, sticky="w", pady=4)
        self.input_display = ttk.Entry(
            input_frame,
            textvariable=self.input_summary_var,
            state="readonly",
        )
        self.input_display.grid(row=1, column=1, sticky="ew", padx=(0, 10), pady=4)
        self.select_button = ttk.Button(input_frame, text="Select file...", command=self._select_input)
        self.select_button.grid(row=1, column=2, sticky="e", pady=4)

        output_frame = ttk.LabelFrame(main, text="Output configuration", padding=12)
        output_frame.grid(row=2, column=0, sticky="ew", pady=(0, 10))
        output_frame.columnconfigure(1, weight=1)

        ttk.Label(output_frame, text="Output Markdown:").grid(row=0, column=0, sticky="w", pady=4)
        self.output_entry = ttk.Entry(output_frame, textvariable=self.output_path_var)
        self.output_entry.grid(row=0, column=1, sticky="ew", padx=(0, 10), pady=4)
        self.save_as_button = ttk.Button(output_frame, text="Save as...", command=self._browse_output)
        self.save_as_button.grid(row=0, column=2, sticky="e", pady=4)

        selection_frame = ttk.Frame(main)
        selection_frame.grid(row=3, column=0, sticky="ew")
        selection_frame.columnconfigure(0, weight=1)
        selection_frame.columnconfigure(1, weight=1)

        format_frame = ttk.LabelFrame(selection_frame, text="Format selection", padding=12)
        format_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 8), pady=(0, 10))
        format_frame.columnconfigure(0, weight=1)

        ttk.Checkbutton(format_frame, text="PDF", variable=self.pdf_enabled_var).grid(
            row=0, column=0, sticky="w", pady=2
        )
        ttk.Checkbutton(format_frame, text="Word DOCX", variable=self.docx_enabled_var).grid(
            row=1, column=0, sticky="w", pady=2
        )
        ttk.Checkbutton(format_frame, text="PowerPoint PPTX", variable=self.pptx_enabled_var).grid(
            row=2, column=0, sticky="w", pady=2
        )

        options_frame = ttk.LabelFrame(selection_frame, text="Conversion options", padding=12)
        options_frame.grid(row=0, column=1, sticky="nsew", pady=(0, 10))
        options_frame.columnconfigure(0, weight=1)
        options_frame.columnconfigure(1, weight=1)

        ttk.Checkbutton(
            options_frame,
            text="Include document metadata",
            variable=self.include_metadata_var,
        ).grid(row=0, column=0, sticky="w", pady=2)
        ttk.Checkbutton(
            options_frame,
            text="Include page/slide separators",
            variable=self.include_page_slide_separators_var,
        ).grid(row=0, column=1, sticky="w", pady=2)
        ttk.Checkbutton(
            options_frame,
            text="Detect headings automatically",
            variable=self.detect_headings_var,
        ).grid(row=1, column=0, sticky="w", pady=2)
        ttk.Checkbutton(
            options_frame,
            text="Normalize whitespace",
            variable=self.normalize_whitespace_var,
        ).grid(row=1, column=1, sticky="w", pady=2)
        ttk.Checkbutton(
            options_frame,
            text="Optimize Markdown for AI reading",
            variable=self.optimize_for_ai_var,
        ).grid(row=2, column=0, sticky="w", pady=2)
        self.include_subfolders_check = ttk.Checkbutton(
            options_frame,
            text="Include subfolders",
            variable=self.include_subfolders_var,
        )
        self.include_subfolders_check.grid(row=2, column=1, sticky="w", pady=2)
        ttk.Checkbutton(
            options_frame,
            text="Overwrite existing Markdown files",
            variable=self.overwrite_existing_var,
        ).grid(row=3, column=0, sticky="w", pady=2)

        progress_frame = ttk.LabelFrame(main, text="Progress", padding=12)
        progress_frame.grid(row=4, column=0, sticky="ew", pady=(0, 10))
        progress_frame.columnconfigure(0, weight=1)

        self.progress_bar = ttk.Progressbar(progress_frame, mode="determinate")
        self.progress_bar.grid(row=0, column=0, sticky="ew")
        ttk.Label(progress_frame, textvariable=self.status_var).grid(row=1, column=0, sticky="w", pady=(8, 0))

        log_frame = ttk.LabelFrame(main, text="Log", padding=12)
        log_frame.grid(row=5, column=0, sticky="nsew", pady=(0, 10))
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)

        self.log_text = tk.Text(log_frame, height=14, wrap="word", state="disabled")
        self.log_text.grid(row=0, column=0, sticky="nsew")
        log_scrollbar = ttk.Scrollbar(log_frame, orient="vertical", command=self.log_text.yview)
        log_scrollbar.grid(row=0, column=1, sticky="ns")
        self.log_text.configure(yscrollcommand=log_scrollbar.set)

        button_frame = ttk.Frame(main)
        button_frame.grid(row=6, column=0, sticky="e")

        self.convert_button = ttk.Button(button_frame, text="Convert", command=self._start_conversion)
        self.convert_button.grid(row=0, column=0, padx=(0, 8))
        self.clear_button = ttk.Button(button_frame, text="Clear", command=self._clear_inputs)
        self.clear_button.grid(row=0, column=1, padx=(0, 8))
        self.dependency_button = ttk.Button(
            button_frame,
            text="Check / Install Dependencies",
            command=self._check_or_install_dependencies,
        )
        self.dependency_button.grid(row=0, column=2, padx=(0, 8))
        ttk.Button(button_frame, text="Exit", command=self.destroy).grid(row=0, column=3)

    def _append_log(self, message: str) -> None:
        timestamp = datetime.now().strftime("%H:%M:%S")
        lines = message.splitlines() or [message]

        self.log_text.configure(state="normal")
        for line in lines:
            self.log_text.insert("end", f"[{timestamp}] {line}\n")
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

    def _post_log(self, message: str) -> None:
        self.after(0, lambda text=message: self._append_log(text))

    def _set_status(self, message: str) -> None:
        self.status_var.set(message)

    def _post_status(self, message: str) -> None:
        self.after(0, lambda text=message: self._set_status(text))

    def _set_progress(self, completed: int, total: int) -> None:
        self.progress_bar.configure(maximum=max(total, 1), value=completed)

    def _post_progress(self, completed: int, total: int) -> None:
        self.after(0, lambda done=completed, count=total: self._set_progress(done, count))

    def _refresh_widget_states(self) -> None:
        busy = self.install_running or self.conversion_running
        selected_mode = self.input_mode_var.get()

        self.mode_combo.configure(state="disabled" if busy else "readonly")
        self.select_button.configure(state="disabled" if busy else "normal")
        self.convert_button.configure(state="disabled" if busy else "normal")
        self.clear_button.configure(state="disabled" if busy else "normal")
        self.dependency_button.configure(state="disabled" if busy else "normal")

        if busy:
            self.output_entry.configure(state="disabled")
            self.save_as_button.configure(state="disabled")
            self.include_subfolders_check.configure(state="disabled")
            return

        if selected_mode == MODE_SINGLE:
            self.output_entry.configure(state="normal")
            self.save_as_button.configure(state="normal")
        else:
            self.output_entry.configure(state="disabled")
            self.save_as_button.configure(state="disabled")

        if selected_mode == MODE_FOLDER:
            self.include_subfolders_check.configure(state="normal")
        else:
            self.include_subfolders_check.configure(state="disabled")

    def _on_mode_changed(self, _event: object) -> None:
        self._handle_mode_change(clear_selection=True)

    def _handle_mode_change(self, clear_selection: bool) -> None:
        if clear_selection:
            self.single_input_path = None
            self.multiple_input_paths = []
            self.folder_input_path = None
            self.input_summary_var.set("")
            self.output_path_var.set("")

        mode = self.input_mode_var.get()
        if mode == MODE_SINGLE:
            self.select_button.configure(text="Select file...")
        elif mode == MODE_MULTIPLE:
            self.select_button.configure(text="Select files...")
        else:
            self.select_button.configure(text="Select folder...")

        self._refresh_widget_states()
        self._append_log(f"Input mode set to: {mode}")

    def _select_input(self) -> None:
        mode = self.input_mode_var.get()

        if mode == MODE_SINGLE:
            selected = filedialog.askopenfilename(
                title="Select document",
                filetypes=FILE_DIALOG_TYPES,
            )
            if not selected:
                return

            self.single_input_path = Path(selected)
            self.multiple_input_paths = []
            self.folder_input_path = None
            self.input_summary_var.set(str(self.single_input_path))
            self.output_path_var.set(str(self.single_input_path.with_suffix(".md")))
            self._append_log(f"Selected single file: {self.single_input_path}")
        elif mode == MODE_MULTIPLE:
            selected = filedialog.askopenfilenames(
                title="Select documents",
                filetypes=FILE_DIALOG_TYPES,
            )
            if not selected:
                return

            self.single_input_path = None
            self.multiple_input_paths = [Path(item) for item in selected]
            self.folder_input_path = None
            file_count = len(self.multiple_input_paths)
            self.input_summary_var.set(f"{file_count} files selected")
            self.output_path_var.set("")
            self._append_log(f"Selected multiple files: {file_count} files")
        else:
            selected = filedialog.askdirectory(title="Select folder")
            if not selected:
                return

            self.single_input_path = None
            self.multiple_input_paths = []
            self.folder_input_path = Path(selected)
            self.input_summary_var.set(str(self.folder_input_path))
            self.output_path_var.set("")
            self._append_log(f"Selected folder: {self.folder_input_path}")

    def _browse_output(self) -> None:
        initial_file = "output.md"
        if self.single_input_path is not None:
            initial_file = self.single_input_path.with_suffix(".md").name

        selected = filedialog.asksaveasfilename(
            title="Save Markdown file as",
            defaultextension=".md",
            initialfile=initial_file,
            filetypes=[("Markdown files", "*.md"), ("All files", "*.*")],
        )
        if selected:
            self.output_path_var.set(selected)
            self._append_log(f"Selected output Markdown path: {selected}")

    def _clear_inputs(self) -> None:
        self.single_input_path = None
        self.multiple_input_paths = []
        self.folder_input_path = None
        self.input_summary_var.set("")
        self.output_path_var.set("")
        self.progress_bar.configure(value=0, maximum=1)
        self.status_var.set("Ready.")
        self.log_text.configure(state="normal")
        self.log_text.delete("1.0", "end")
        self.log_text.configure(state="disabled")
        self._refresh_widget_states()

    def _startup_dependency_check(self) -> None:
        self._append_log("Checking converter dependencies on startup.")
        for line in self.dependency_manager.get_status_lines():
            self._append_log(line)

        missing = self.dependency_manager.get_missing_dependencies()
        if not missing:
            self._append_log("All dependencies are already installed.")
            return

        message = (
            "Some optional converter dependencies are missing:\n\n"
            f"{self.dependency_manager.format_dependency_list(missing)}\n\n"
            "Do you want to install them automatically now?"
        )
        if messagebox.askyesno("Missing dependencies", message):
            self._start_dependency_installation(missing)
        else:
            self._append_log("Automatic dependency installation was skipped by the user.")

    def _check_or_install_dependencies(self) -> None:
        self._append_log("Dependency check requested by the user.")
        for line in self.dependency_manager.get_status_lines():
            self._append_log(line)

        missing = self.dependency_manager.get_missing_dependencies()
        if not missing:
            self.status_var.set("All dependencies are installed.")
            messagebox.showinfo("Dependencies", "All converter dependencies are already installed.")
            return

        message = (
            "The following dependencies are missing:\n\n"
            f"{self.dependency_manager.format_dependency_list(missing)}\n\n"
            "Do you want to install them automatically now?"
        )
        if messagebox.askyesno("Install dependencies", message):
            self._start_dependency_installation(missing)
        else:
            self._append_log("Dependency installation canceled by the user.")

    def _start_dependency_installation(self, missing: list[Dependency]) -> None:
        if self.install_running or self.conversion_running:
            return

        self.install_running = True
        self.status_var.set("Installing dependencies...")
        self._refresh_widget_states()

        thread = threading.Thread(
            target=self._install_dependencies_in_background,
            args=(missing,),
            daemon=True,
        )
        thread.start()

    def _install_dependencies_in_background(self, missing: list[Dependency]) -> None:
        success, message, _remaining = self.dependency_manager.install_missing_dependencies(
            missing,
            self._post_log,
        )
        self.after(0, lambda ok=success, text=message: self._dependency_installation_finished(ok, text))

    def _dependency_installation_finished(self, success: bool, message: str) -> None:
        self.install_running = False
        self._refresh_widget_states()

        if success:
            self.status_var.set("Dependencies are ready.")
            self._append_log(message)
            messagebox.showinfo("Dependency installation", message)
        else:
            self.status_var.set("Dependency installation finished with warnings.")
            self._append_log(message)
            messagebox.showwarning("Dependency installation", message)

    def _get_conversion_options(self) -> ConversionOptions:
        enabled_extensions: set[str] = set()
        if self.pdf_enabled_var.get():
            enabled_extensions.add(".pdf")
        if self.docx_enabled_var.get():
            enabled_extensions.add(".docx")
        if self.pptx_enabled_var.get():
            enabled_extensions.add(".pptx")

        if not enabled_extensions:
            raise ValueError("No format checkbox is selected. Please enable at least one format.")

        return ConversionOptions(
            include_metadata=self.include_metadata_var.get(),
            include_page_slide_separators=self.include_page_slide_separators_var.get(),
            detect_headings=self.detect_headings_var.get(),
            normalize_whitespace=self.normalize_whitespace_var.get(),
            optimize_for_ai=self.optimize_for_ai_var.get(),
            include_subfolders=self.include_subfolders_var.get(),
            overwrite_existing=self.overwrite_existing_var.get(),
            enabled_extensions=enabled_extensions,
        )

    def _start_conversion(self) -> None:
        if self.install_running or self.conversion_running:
            return

        try:
            options = self._get_conversion_options()
            jobs, scan_summary = self._build_conversion_jobs(options)
        except ValueError as exc:
            message = str(exc)
            self._append_log(message)
            self.status_var.set(message)
            if message.startswith("Please select"):
                messagebox.showwarning("No input selected", message)
            return

        if not jobs:
            message = str(scan_summary.get("warning_message", "No files are ready for conversion."))
            self._append_log(message)
            self.status_var.set(message)
            messagebox.showwarning("No files to convert", message)
            return

        self.conversion_running = True
        self.progress_bar.configure(value=0, maximum=max(len(jobs), 1))
        self.status_var.set(f"Converting 0 of {len(jobs)} files...")
        self._refresh_widget_states()
        self._append_log("Conversion started.")
        self._append_log(f"Total jobs created: {len(jobs)}")

        thread = threading.Thread(
            target=self._convert_jobs_in_background,
            args=(jobs, options, scan_summary),
            daemon=True,
        )
        thread.start()

    def _build_conversion_jobs(
        self,
        options: ConversionOptions,
    ) -> tuple[list[ConversionJob], dict[str, object]]:
        mode = self.input_mode_var.get()
        jobs: list[ConversionJob] = []
        output_folders: set[str] = set()
        skipped_files = 0
        total_files_found = 0
        supported_files_found = 0
        warning_message = ""

        if mode == MODE_SINGLE:
            if self.single_input_path is None:
                raise ValueError("Please select a file to convert.")
            if not self.single_input_path.exists():
                raise ValueError(f"File does not exist: {self.single_input_path}")

            total_files_found = 1
            extension = self.single_input_path.suffix.lower()
            if extension not in SUPPORTED_EXTENSIONS:
                raise ValueError("Unsupported file type. Supported files are .pdf, .docx, and .pptx.")
            if extension not in options.enabled_extensions:
                raise ValueError("The selected file type is currently disabled in Format selection.")

            output_value = self.output_path_var.get().strip()
            if not output_value:
                raise ValueError("No selected output path in single-file mode.")

            output_path = build_output_path(
                source_path=self.single_input_path,
                mode=MODE_SINGLE,
                overwrite_existing=options.overwrite_existing,
                explicit_output_path=Path(output_value),
            )
            job = ConversionJob(
                input_path=self.single_input_path,
                output_path=output_path,
                source_type=SOURCE_TYPE_BY_EXTENSION[extension],
            )
            jobs.append(job)
            output_folders.add(str(output_path.parent))
            supported_files_found = 1
        elif mode == MODE_MULTIPLE:
            if not self.multiple_input_paths:
                raise ValueError("Please select one or more files to convert.")

            total_files_found = len(self.multiple_input_paths)
            for source_path in self.multiple_input_paths:
                job = self._build_batch_job(source_path, mode, options)
                if job is None:
                    skipped_files += 1
                    continue
                jobs.append(job)
                output_folders.add(str(job.output_path.parent))
                supported_files_found += 1
        else:
            if self.folder_input_path is None:
                raise ValueError("Please select a folder to convert.")
            if not self.folder_input_path.exists() or not self.folder_input_path.is_dir():
                raise ValueError(f"Invalid folder: {self.folder_input_path}")

            iterator = (
                self.folder_input_path.rglob("*")
                if options.include_subfolders
                else self.folder_input_path.glob("*")
            )
            files = sorted(path for path in iterator if path.is_file())
            total_files_found = len(files)

            unsupported_count = 0
            disabled_count = 0

            for source_path in files:
                extension = source_path.suffix.lower()
                if extension in SUPPORTED_EXTENSIONS:
                    supported_files_found += 1
                if extension not in SUPPORTED_EXTENSIONS:
                    unsupported_count += 1
                    skipped_files += 1
                    continue
                if extension not in options.enabled_extensions:
                    disabled_count += 1
                    skipped_files += 1
                    continue

                job = self._build_batch_job(
                    source_path=source_path,
                    mode=mode,
                    options=options,
                    selected_folder=self.folder_input_path,
                    log_skip=False,
                )
                if job is None:
                    skipped_files += 1
                    continue
                jobs.append(job)
                output_folders.add(str(job.output_path.parent))

            if total_files_found == 0:
                warning_message = "No files were found in the selected folder."
                self._append_log(warning_message)
                self.status_var.set(warning_message)
                return [], {
                    "total_files_found": 0,
                    "jobs_created": 0,
                    "skipped_files": 0,
                    "output_folders": [],
                    "warning_message": warning_message,
                }

            if supported_files_found == 0:
                warning_message = "No supported files were found in the selected folder."
                self._append_log(warning_message)
                self.status_var.set(warning_message)
                return [], {
                    "total_files_found": total_files_found,
                    "jobs_created": 0,
                    "skipped_files": skipped_files,
                    "output_folders": [],
                    "warning_message": warning_message,
                }

            if unsupported_count:
                self._append_log(
                    f"Skipped {unsupported_count} unsupported files while scanning the folder."
                )
            if disabled_count:
                self._append_log(
                    f"Skipped {disabled_count} files because their formats are disabled in Format selection."
                )

        if not jobs and total_files_found > 0:
            warning_message = "No conversion jobs were created with the current input and format settings."
            self._append_log(warning_message)

        return jobs, {
            "total_files_found": total_files_found,
            "jobs_created": len(jobs),
            "skipped_files": skipped_files,
            "output_folders": sorted(output_folders),
            "warning_message": warning_message,
        }

    def _build_batch_job(
        self,
        source_path: Path,
        mode: str,
        options: ConversionOptions,
        selected_folder: Optional[Path] = None,
        log_skip: bool = True,
    ) -> Optional[ConversionJob]:
        if not source_path.exists() or not source_path.is_file():
            if log_skip:
                self._append_log(f"Skipped missing or invalid file: {source_path}")
            return None

        extension = source_path.suffix.lower()
        if extension not in SUPPORTED_EXTENSIONS:
            if log_skip:
                self._append_log(f"Skipped unsupported file: {source_path}")
            return None

        if extension not in options.enabled_extensions:
            if log_skip:
                self._append_log(
                    f"Skipped file because its format is disabled: {source_path}"
                )
            return None

        output_path = build_output_path(
            source_path=source_path,
            mode=mode,
            overwrite_existing=options.overwrite_existing,
            selected_folder=selected_folder,
        )
        return ConversionJob(
            input_path=source_path,
            output_path=output_path,
            source_type=SOURCE_TYPE_BY_EXTENSION[extension],
        )

    def _convert_jobs_in_background(
        self,
        jobs: list[ConversionJob],
        options: ConversionOptions,
        scan_summary: dict[str, object],
    ) -> None:
        success_count = 0
        failed_count = 0
        total_jobs = len(jobs)

        for index, job in enumerate(jobs, start=1):
            self._post_status(f"Converting {index} of {total_jobs}: {job.input_path.name}")
            self._post_log(f"Converting file: {job.input_path}")

            try:
                converter = get_converter_for_path(job.input_path, options, self.dependency_manager)
                result = converter.convert(job)
            except Exception as exc:
                result = ConversionResult(job.input_path, job.output_path, False, str(exc))

            if result.success:
                success_count += 1
                self._post_log(f"File converted successfully: {result.input_path}")
                self._post_log(f"Output path: {result.output_path}")
            else:
                failed_count += 1
                self._post_log(f"File failed: {result.input_path}")
                self._post_log(f"Failure reason: {result.message}")

            self._post_progress(index, total_jobs)

        self.after(
            0,
            lambda: self._conversion_finished(
                total_jobs=total_jobs,
                success_count=success_count,
                failed_count=failed_count,
                scan_summary=scan_summary,
            ),
        )

    def _conversion_finished(
        self,
        total_jobs: int,
        success_count: int,
        failed_count: int,
        scan_summary: dict[str, object],
    ) -> None:
        self.conversion_running = False
        self._refresh_widget_states()
        self.progress_bar.configure(value=max(total_jobs, 0), maximum=max(total_jobs, 1))

        skipped_files = int(scan_summary.get("skipped_files", 0))
        output_folders = scan_summary.get("output_folders", [])
        output_folder_text = "\n".join(str(folder) for folder in output_folders) or "No output folders were used."

        summary_lines = [
            f"Total files found: {scan_summary.get('total_files_found', 0)}",
            f"Total jobs created: {scan_summary.get('jobs_created', 0)}",
            f"Successfully converted: {success_count}",
            f"Failed conversions: {failed_count}",
            f"Skipped files: {skipped_files}",
            "Output folder or folders used:",
            output_folder_text,
        ]
        summary_message = "\n".join(summary_lines)

        self._append_log("Conversion summary:")
        self._append_log(summary_message)

        if success_count > 0:
            self.status_var.set(
                f"Completed. {success_count} succeeded, {failed_count} failed, {skipped_files} skipped."
            )
            messagebox.showinfo("Conversion completed", summary_message)
        else:
            self.status_var.set("Conversion failed completely.")
            messagebox.showerror("Conversion failed", summary_message)


def main() -> int:
    app = DocumentToMarkdownApp()
    app.mainloop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
