# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-06-08

### Added

- Graphical converter for PDF, Word DOCX, and PowerPoint PPTX documents to Markdown.
- Single file, multiple files, and folder (with optional recursion) conversion modes.
- Inline formatting fidelity: bold, italic, and hyperlinks are preserved for DOCX and PPTX.
- Font-size aware heading detection for PDF documents using `pdfminer.six`.
- Flexible output: optional document header, optional table of contents, and a choice
  between a blockquote header and YAML front matter.
- Optional embedded image extraction into a sidecar `<name>_assets` folder.
- Optional OCR of scanned PDF pages through the `ocr` extra (`pytesseract`).
- Conversion controls: cancel a running batch, open the output folder, and export the log.
- Optional drag-and-drop of files and folders through the `dnd` extra (`tkinterdnd2`).
- Bilingual interface (English and Portuguese) with a persisted language preference.
- Windows launcher (`run.vbs`) that provisions a private virtual environment on first run
  and reuses it on subsequent launches.
- Standalone executable build via PyInstaller (`doc2md.spec`).

[1.0.0]: https://github.com/Rui-Casaca/MarkDown_converter/releases/tag/v1.0.0
