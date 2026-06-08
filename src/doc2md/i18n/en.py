"""English UI string catalog for doc2md."""

from __future__ import annotations

CATALOG: dict[str, str] = {
    # Header
    "app.subtitle": (
        "Convert PDF, Word DOCX, and PowerPoint PPTX documents into clean Markdown "
        "optimized for AI reading, summarization, embeddings, RAG ingestion, and question answering."
    ),
    "label.language": "Language:",
    # Frame titles
    "frame.input": "Input configuration",
    "frame.output": "Output configuration",
    "frame.format": "Format selection",
    "frame.options": "Conversion options",
    "frame.progress": "Progress",
    "frame.log": "Log",
    # Labels
    "label.input_mode": "Input mode:",
    "label.selected_input": "Selected input:",
    "label.output_markdown": "Output Markdown:",
    "label.header_style": "Header style:",
    "input.files_selected": "{n} files selected",
    # Input mode combobox values
    "mode.single": "Single file",
    "mode.multiple": "Multiple files",
    "mode.folder": "Folder",
    # Header style combobox values
    "headerstyle.blockquote": "Blockquote",
    "headerstyle.yaml": "YAML front matter",
    # Conversion option checkboxes
    "check.metadata": "Include document metadata",
    "check.separators": "Include page/slide separators",
    "check.headings": "Detect headings automatically",
    "check.whitespace": "Normalize whitespace",
    "check.optimize_ai": "Optimize Markdown for AI reading",
    "check.subfolders": "Include subfolders",
    "check.overwrite": "Overwrite existing Markdown files",
    "check.header": "Include document header",
    "check.toc": "Include table of contents",
    "check.images": "Extract embedded images",
    "check.ocr": "Run OCR on scanned PDF pages",
    # Buttons
    "button.select_file": "Select file...",
    "button.select_files": "Select files...",
    "button.select_folder": "Select folder...",
    "button.save_as": "Save as...",
    "button.convert": "Convert",
    "button.cancel": "Cancel",
    "button.open_output": "Open output folder",
    "button.export_log": "Export log",
    "button.clear": "Clear",
    "button.dependencies": "Check / Install Dependencies",
    "button.exit": "Exit",
    # Status bar
    "status.ready": "Ready.",
    "status.installing_deps": "Installing dependencies...",
    "status.deps_ready": "Dependencies are ready.",
    "status.deps_warning": "Dependency installation finished with warnings.",
    "status.deps_all_installed": "All dependencies are installed.",
    "status.converting_init": "Converting 0 of {total} files...",
    "status.converting_file": "Converting {index} of {total}: {name}",
    "status.completed": "Completed. {ok} succeeded, {failed} failed, {skipped} skipped.",
    "status.failed": "Conversion failed completely.",
    "status.canceled": "Canceled. {ok} converted before stopping, {failed} failed.",
    "status.canceling": "Canceling after the current file...",
    # Dialogs
    "dialog.missing_deps.title": "Missing dependencies",
    "dialog.missing_deps.body": (
        "Some optional converter dependencies are missing:\n\n{list}\n\n"
        "Do you want to install them automatically now?"
    ),
    "dialog.deps.title": "Dependencies",
    "dialog.deps.all_installed": "All converter dependencies are already installed.",
    "dialog.install_deps.title": "Install dependencies",
    "dialog.install_deps.body": (
        "The following dependencies are missing:\n\n{list}\n\n"
        "Do you want to install them automatically now?"
    ),
    "dialog.dep_install.title": "Dependency installation",
    "dialog.no_input.title": "No input selected",
    "dialog.no_files.title": "No files to convert",
    "dialog.completed.title": "Conversion completed",
    "dialog.failed.title": "Conversion failed",
    "dialog.canceled.title": "Conversion canceled",
    "dialog.open_output.title": "Open output folder",
    "dialog.open_output.none": "No output folder is available yet.",
    "dialog.open_output.error": "Could not open the folder:\n{error}",
    "dialog.export_log.title": "Export log",
    "dialog.export_log.empty": "The log is empty.",
    "dialog.export_log.error": "Could not export the log:\n{error}",
    # File dialogs
    "filedialog.select_document": "Select document",
    "filedialog.select_documents": "Select documents",
    "filedialog.select_folder": "Select folder",
    "filedialog.save_as": "Save Markdown file as",
    "filedialog.export_log": "Export log to file",
    # Conversion summary
    "summary.total_found": "Total files found: {n}",
    "summary.jobs_created": "Total jobs created: {n}",
    "summary.succeeded": "Successfully converted: {n}",
    "summary.failed": "Failed conversions: {n}",
    "summary.skipped": "Skipped files: {n}",
    "summary.output_header": "Output folder or folders used:",
    "summary.no_output": "No output folders were used.",
    # Validation and scan warnings
    "err.no_format": "No format checkbox is selected. Please enable at least one format.",
    "err.select_file": "Please select a file to convert.",
    "err.file_missing": "File does not exist: {path}",
    "err.unsupported": "Unsupported file type. Supported files are .pdf, .docx, and .pptx.",
    "err.disabled_type": "The selected file type is currently disabled in Format selection.",
    "err.no_output_path": "No selected output path in single-file mode.",
    "err.select_files": "Please select one or more files to convert.",
    "err.select_folder": "Please select a folder to convert.",
    "err.invalid_folder": "Invalid folder: {path}",
    "warn.no_files_in_folder": "No files were found in the selected folder.",
    "warn.no_supported_in_folder": "No supported files were found in the selected folder.",
    "warn.no_jobs": "No conversion jobs were created with the current input and format settings.",
    "warn.no_files_ready": "No files are ready for conversion.",
}
