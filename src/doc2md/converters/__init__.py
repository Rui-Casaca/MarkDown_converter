"""Document converters for PDF, Word DOCX, and PowerPoint PPTX inputs."""

from __future__ import annotations

from .base import DocumentToMarkdownConverter, build_output_path
from .comments import Comment, render_comment_callout
from .docx import DocxMarkdownConverter
from .factory import get_converter_for_path
from .pdf import PdfMarkdownConverter
from .pptx import PptxMarkdownConverter

__all__ = [
    "Comment",
    "DocumentToMarkdownConverter",
    "DocxMarkdownConverter",
    "PdfMarkdownConverter",
    "PptxMarkdownConverter",
    "build_output_path",
    "get_converter_for_path",
    "render_comment_callout",
]
