"""Core data models and shared constants for doc2md."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

APP_TITLE = "Document to Markdown Converter"
OUTPUT_FOLDER_NAME = "MarkDowns_converted"
SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".pptx"}
MODE_SINGLE = "Single file"
MODE_MULTIPLE = "Multiple files"
MODE_FOLDER = "Folder"
MANUAL_INSTALL_COMMAND = "python -m pip install pypdf python-docx python-pptx"
HEADER_STYLE_BLOCKQUOTE = "Blockquote"
HEADER_STYLE_YAML = "YAML front matter"
HEADER_STYLES = [HEADER_STYLE_BLOCKQUOTE, HEADER_STYLE_YAML]
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
    include_header: bool = True
    include_toc: bool = True
    header_style: str = HEADER_STYLE_BLOCKQUOTE
    extract_images: bool = False
    enable_ocr: bool = False
    include_comments: bool = False
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
OCR_DEPENDENCY = Dependency(
    display_name="pytesseract",
    import_name="pytesseract",
    package_name="pytesseract",
    required_for="OCR of scanned PDF pages",
)
