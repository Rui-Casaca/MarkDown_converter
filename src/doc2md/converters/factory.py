"""Factory that selects the right converter for a given file extension."""

from __future__ import annotations

from pathlib import Path

from ..dependencies import DependencyManager
from ..models import ConversionOptions
from .base import DocumentToMarkdownConverter
from .docx import DocxMarkdownConverter
from .pdf import PdfMarkdownConverter
from .pptx import PptxMarkdownConverter


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
