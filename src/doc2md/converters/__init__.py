"""Document converters for PDF, Word DOCX, and PowerPoint PPTX inputs."""

from __future__ import annotations

from .base import DocumentToMarkdownConverter, build_output_path
from .docx import DocxMarkdownConverter
from .factory import get_converter_for_path
from .pdf import PdfMarkdownConverter
from .pptx import PptxMarkdownConverter

__all__ = [
    "DocumentToMarkdownConverter",
    "DocxMarkdownConverter",
    "PdfMarkdownConverter",
    "PptxMarkdownConverter",
    "build_output_path",
    "get_converter_for_path",
]
