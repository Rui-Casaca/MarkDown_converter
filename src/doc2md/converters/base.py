"""Base converter class and output-path resolution."""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path

from ..dependencies import DependencyManager
from ..markdown_utils import MarkdownUtils
from ..models import (
    HEADER_STYLE_YAML,
    MANUAL_INSTALL_COMMAND,
    MODE_FOLDER,
    MODE_MULTIPLE,
    MODE_SINGLE,
    OUTPUT_FOLDER_NAME,
    ConversionJob,
    ConversionOptions,
    ConversionResult,
    Dependency,
)
from .assets import AssetWriter


def build_output_path(
    source_path: Path,
    mode: str,
    overwrite_existing: bool,
    selected_folder: Path | None = None,
    explicit_output_path: Path | None = None,
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

            output_path = job.output_path
            if output_path.exists() and not self.options.overwrite_existing:
                output_path = MarkdownUtils.unique_output_path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)

            asset_writer = AssetWriter(output_path) if self.options.extract_images else None
            title, metadata, content = self.extract(job.input_path, asset_writer)

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

    def extract(
        self,
        input_path: Path,
        asset_writer: AssetWriter | None = None,
    ) -> tuple[str, dict[str, str], str]:
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

        header_items = self._header_items(input_path, metadata)
        use_yaml = self.options.include_header and self.options.header_style == HEADER_STYLE_YAML

        parts: list[str] = []

        if use_yaml:
            parts.append(self._render_yaml_front_matter(safe_title, header_items))

        parts.append(f"# {safe_title}")

        if self.options.include_header and not use_yaml:
            parts.append(self._render_blockquote_header(header_items))

        if self.options.include_toc:
            toc = MarkdownUtils.generate_table_of_contents(content_body)
            parts.append(f"## Table of Contents\n\n{toc}")

        parts.append(f"## Content\n\n{content_body}")
        parts.append("---\n\n_Conversion completed by Document to Markdown Converter._")

        markdown = "\n\n".join(parts)
        return MarkdownUtils.sanitize_markdown(markdown).rstrip() + "\n"

    def _header_items(self, input_path: Path, metadata: dict[str, str]) -> list[tuple[str, str]]:
        """Return ordered provenance (label, value) pairs used to render the header."""
        items: list[tuple[str, str]] = [
            ("Source file", input_path.name),
            ("Source type", self.source_type),
            ("Conversion date", datetime.now().strftime("%Y-%m-%d %H:%M")),
            ("AI-readable format", "enabled" if self.options.optimize_for_ai else "disabled"),
        ]
        if self.options.include_metadata:
            for key, value in metadata.items():
                if value:
                    items.append((key, value))
        return items

    @staticmethod
    def _render_blockquote_header(items: list[tuple[str, str]]) -> str:
        lines = ["> Converted to Markdown."]
        for label, value in items:
            if label == "Source file":
                lines.append(f"> {label}: `{value}`")
            else:
                lines.append(f"> {label}: {value}")
        return "\n".join(lines)

    @classmethod
    def _render_yaml_front_matter(cls, title: str, items: list[tuple[str, str]]) -> str:
        lines = ["---", f"title: {cls._yaml_scalar(title)}"]
        for label, value in items:
            lines.append(f"{cls._yaml_key(label)}: {cls._yaml_scalar(value)}")
        lines.append("---")
        return "\n".join(lines)

    @staticmethod
    def _yaml_key(label: str) -> str:
        key = re.sub(r"[^\w]+", "_", label.strip().lower()).strip("_")
        return key or "field"

    @staticmethod
    def _yaml_scalar(value: str) -> str:
        escaped = value.replace("\\", "\\\\").replace('"', '\\"')
        return f'"{escaped}"'

    def _missing_dependency_message(self) -> str:
        return (
            f"Missing dependency for {self.source_type} conversion: {self.dependency.display_name}.\n"
            f"Install it with:\n{MANUAL_INSTALL_COMMAND}"
        )
