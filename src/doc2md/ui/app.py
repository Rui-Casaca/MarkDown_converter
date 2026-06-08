"""Tkinter GUI application for converting documents to Markdown."""

from __future__ import annotations

import os
import subprocess
import sys
import threading
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from ..converters import build_output_path, get_converter_for_path
from ..dependencies import DependencyManager
from ..i18n import (
    LANGUAGE_LABELS,
    LANGUAGES,
    current_language,
    label_for_language,
    language_for_label,
    set_language,
    t,
)
from ..models import (
    APP_TITLE,
    DOCX_DEPENDENCY,
    FILE_DIALOG_TYPES,
    HEADER_STYLE_BLOCKQUOTE,
    HEADER_STYLE_YAML,
    MODE_FOLDER,
    MODE_MULTIPLE,
    MODE_SINGLE,
    PDF_DEPENDENCY,
    PPTX_DEPENDENCY,
    SOURCE_TYPE_BY_EXTENSION,
    SUPPORTED_EXTENSIONS,
    ConversionJob,
    ConversionOptions,
    ConversionResult,
    Dependency,
)
from ..settings import load_language, save_language
from .dnd import enable_drag_and_drop, register_drop_target

MODE_ORDER: tuple[str, ...] = (MODE_SINGLE, MODE_MULTIPLE, MODE_FOLDER)
MODE_KEYS: dict[str, str] = {
    MODE_SINGLE: "mode.single",
    MODE_MULTIPLE: "mode.multiple",
    MODE_FOLDER: "mode.folder",
}
HEADER_ORDER: tuple[str, ...] = (HEADER_STYLE_BLOCKQUOTE, HEADER_STYLE_YAML)
HEADER_KEYS: dict[str, str] = {
    HEADER_STYLE_BLOCKQUOTE: "headerstyle.blockquote",
    HEADER_STYLE_YAML: "headerstyle.yaml",
}


class _InputSelectionError(ValueError):
    """Raised when the user has not chosen any input to convert."""


class DocumentToMarkdownApp(tk.Tk):
    """Tkinter application for converting PDF, DOCX, and PPTX files to Markdown."""

    def __init__(self) -> None:
        super().__init__()
        self.title(APP_TITLE)
        self.geometry("900x650")
        self.minsize(820, 560)

        set_language(load_language(current_language()))

        self.dependencies = [PDF_DEPENDENCY, DOCX_DEPENDENCY, PPTX_DEPENDENCY]
        self.dependency_manager = DependencyManager(self.dependencies)

        self.single_input_path: Path | None = None
        self.multiple_input_paths: list[Path] = []
        self.folder_input_path: Path | None = None
        self.install_running = False
        self.conversion_running = False
        self.cancel_event = threading.Event()
        self.last_output_folders: list[Path] = []
        self._main_frame: ttk.Frame | None = None

        self.input_mode_var = tk.StringVar(value=MODE_SINGLE)
        self.mode_display_var = tk.StringVar()
        self.input_summary_var = tk.StringVar()
        self.output_path_var = tk.StringVar()
        self.status_var = tk.StringVar(value=t("status.ready"))
        self.language_var = tk.StringVar(value=label_for_language(current_language()))

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
        self.include_header_var = tk.BooleanVar(value=True)
        self.include_toc_var = tk.BooleanVar(value=True)
        self.header_style_var = tk.StringVar(value=HEADER_STYLE_BLOCKQUOTE)
        self.header_style_display_var = tk.StringVar()
        self.extract_images_var = tk.BooleanVar(value=False)
        self.enable_ocr_var = tk.BooleanVar(value=False)

        self._build_ui()
        self._handle_mode_change(clear_selection=False)
        self._setup_drag_and_drop()
        self.after(200, self._startup_dependency_check)


    def _build_ui(self) -> None:
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        main = ttk.Frame(self, padding=16)
        main.grid(row=0, column=0, sticky="nsew")
        main.columnconfigure(0, weight=1)
        main.rowconfigure(5, weight=1)
        self._main_frame = main

        header_frame = ttk.Frame(main)
        header_frame.grid(row=0, column=0, sticky="ew")
        header_frame.columnconfigure(0, weight=1)

        ttk.Label(header_frame, text=APP_TITLE, font=("TkDefaultFont", 16, "bold")).grid(
            row=0, column=0, sticky="w"
        )

        language_frame = ttk.Frame(header_frame)
        language_frame.grid(row=0, column=1, sticky="e")
        ttk.Label(language_frame, text=t("label.language")).grid(row=0, column=0, sticky="e", padx=(0, 6))
        self.language_combo = ttk.Combobox(
            language_frame,
            textvariable=self.language_var,
            values=[LANGUAGE_LABELS[code] for code in LANGUAGES],
            state="readonly",
            width=12,
        )
        self.language_combo.grid(row=0, column=1, sticky="e")
        self.language_combo.bind("<<ComboboxSelected>>", self._on_language_changed)

        ttk.Label(
            header_frame,
            text=t("app.subtitle"),
            wraplength=850,
        ).grid(row=1, column=0, columnspan=2, sticky="w", pady=(6, 0))

        input_frame = ttk.LabelFrame(main, text=t("frame.input"), padding=12)
        input_frame.grid(row=1, column=0, sticky="ew", pady=(14, 10))
        input_frame.columnconfigure(1, weight=1)

        ttk.Label(input_frame, text=t("label.input_mode")).grid(row=0, column=0, sticky="w", pady=4)
        self.mode_combo = ttk.Combobox(
            input_frame,
            textvariable=self.mode_display_var,
            values=[t(MODE_KEYS[mode]) for mode in MODE_ORDER],
            state="readonly",
            width=18,
        )
        self.mode_combo.grid(row=0, column=1, sticky="w", pady=4)
        self.mode_combo.bind("<<ComboboxSelected>>", self._on_mode_changed)

        ttk.Label(input_frame, text=t("label.selected_input")).grid(row=1, column=0, sticky="w", pady=4)
        self.input_display = ttk.Entry(
            input_frame,
            textvariable=self.input_summary_var,
            state="readonly",
        )
        self.input_display.grid(row=1, column=1, sticky="ew", padx=(0, 10), pady=4)
        self.select_button = ttk.Button(input_frame, text=t("button.select_file"), command=self._select_input)
        self.select_button.grid(row=1, column=2, sticky="e", pady=4)

        output_frame = ttk.LabelFrame(main, text=t("frame.output"), padding=12)
        output_frame.grid(row=2, column=0, sticky="ew", pady=(0, 10))
        output_frame.columnconfigure(1, weight=1)

        ttk.Label(output_frame, text=t("label.output_markdown")).grid(row=0, column=0, sticky="w", pady=4)
        self.output_entry = ttk.Entry(output_frame, textvariable=self.output_path_var)
        self.output_entry.grid(row=0, column=1, sticky="ew", padx=(0, 10), pady=4)
        self.save_as_button = ttk.Button(output_frame, text=t("button.save_as"), command=self._browse_output)
        self.save_as_button.grid(row=0, column=2, sticky="e", pady=4)

        selection_frame = ttk.Frame(main)
        selection_frame.grid(row=3, column=0, sticky="ew")
        selection_frame.columnconfigure(0, weight=1)
        selection_frame.columnconfigure(1, weight=1)

        format_frame = ttk.LabelFrame(selection_frame, text=t("frame.format"), padding=12)
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

        options_frame = ttk.LabelFrame(selection_frame, text=t("frame.options"), padding=12)
        options_frame.grid(row=0, column=1, sticky="nsew", pady=(0, 10))
        options_frame.columnconfigure(0, weight=1)
        options_frame.columnconfigure(1, weight=1)

        ttk.Checkbutton(
            options_frame,
            text=t("check.metadata"),
            variable=self.include_metadata_var,
        ).grid(row=0, column=0, sticky="w", pady=2)
        ttk.Checkbutton(
            options_frame,
            text=t("check.separators"),
            variable=self.include_page_slide_separators_var,
        ).grid(row=0, column=1, sticky="w", pady=2)
        ttk.Checkbutton(
            options_frame,
            text=t("check.headings"),
            variable=self.detect_headings_var,
        ).grid(row=1, column=0, sticky="w", pady=2)
        ttk.Checkbutton(
            options_frame,
            text=t("check.whitespace"),
            variable=self.normalize_whitespace_var,
        ).grid(row=1, column=1, sticky="w", pady=2)
        ttk.Checkbutton(
            options_frame,
            text=t("check.optimize_ai"),
            variable=self.optimize_for_ai_var,
        ).grid(row=2, column=0, sticky="w", pady=2)
        self.include_subfolders_check = ttk.Checkbutton(
            options_frame,
            text=t("check.subfolders"),
            variable=self.include_subfolders_var,
        )
        self.include_subfolders_check.grid(row=2, column=1, sticky="w", pady=2)
        ttk.Checkbutton(
            options_frame,
            text=t("check.overwrite"),
            variable=self.overwrite_existing_var,
        ).grid(row=3, column=0, sticky="w", pady=2)
        ttk.Checkbutton(
            options_frame,
            text=t("check.header"),
            variable=self.include_header_var,
            command=self._on_header_option_changed,
        ).grid(row=3, column=1, sticky="w", pady=2)
        ttk.Checkbutton(
            options_frame,
            text=t("check.toc"),
            variable=self.include_toc_var,
        ).grid(row=4, column=0, sticky="w", pady=2)
        ttk.Checkbutton(
            options_frame,
            text=t("check.images"),
            variable=self.extract_images_var,
        ).grid(row=4, column=1, sticky="w", pady=2)
        ttk.Checkbutton(
            options_frame,
            text=t("check.ocr"),
            variable=self.enable_ocr_var,
        ).grid(row=5, column=0, sticky="w", pady=2)

        header_style_frame = ttk.Frame(options_frame)
        header_style_frame.grid(row=6, column=0, columnspan=2, sticky="w", pady=(4, 0))
        ttk.Label(header_style_frame, text=t("label.header_style")).grid(
            row=0, column=0, sticky="w", padx=(0, 8)
        )
        self.header_style_combo = ttk.Combobox(
            header_style_frame,
            textvariable=self.header_style_display_var,
            values=[t(HEADER_KEYS[style]) for style in HEADER_ORDER],
            state="readonly",
            width=20,
        )
        self.header_style_combo.grid(row=0, column=1, sticky="w")
        self.header_style_combo.bind("<<ComboboxSelected>>", self._on_header_style_changed)

        progress_frame = ttk.LabelFrame(main, text=t("frame.progress"), padding=12)
        progress_frame.grid(row=4, column=0, sticky="ew", pady=(0, 10))
        progress_frame.columnconfigure(0, weight=1)

        self.progress_bar = ttk.Progressbar(progress_frame, mode="determinate")
        self.progress_bar.grid(row=0, column=0, sticky="ew")
        ttk.Label(progress_frame, textvariable=self.status_var).grid(row=1, column=0, sticky="w", pady=(8, 0))

        log_frame = ttk.LabelFrame(main, text=t("frame.log"), padding=12)
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

        self.convert_button = ttk.Button(
            button_frame, text=t("button.convert"), command=self._start_conversion
        )
        self.convert_button.grid(row=0, column=0, padx=(0, 8))
        self.cancel_button = ttk.Button(
            button_frame,
            text=t("button.cancel"),
            command=self._cancel_conversion,
            state="disabled",
        )
        self.cancel_button.grid(row=0, column=1, padx=(0, 8))
        self.open_output_button = ttk.Button(
            button_frame,
            text=t("button.open_output"),
            command=self._open_output_folder,
            state="disabled",
        )
        self.open_output_button.grid(row=0, column=2, padx=(0, 8))
        self.export_log_button = ttk.Button(
            button_frame,
            text=t("button.export_log"),
            command=self._export_log,
        )
        self.export_log_button.grid(row=0, column=3, padx=(0, 8))
        self.clear_button = ttk.Button(button_frame, text=t("button.clear"), command=self._clear_inputs)
        self.clear_button.grid(row=0, column=4, padx=(0, 8))
        self.dependency_button = ttk.Button(
            button_frame,
            text=t("button.dependencies"),
            command=self._check_or_install_dependencies,
        )
        self.dependency_button.grid(row=0, column=5, padx=(0, 8))
        ttk.Button(button_frame, text=t("button.exit"), command=self.destroy).grid(row=0, column=6)

        self._sync_combobox_displays()


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
        self.cancel_button.configure(state="normal" if self.conversion_running else "disabled")
        self.open_output_button.configure(
            state="normal" if (not busy and self.last_output_folders) else "disabled"
        )

        if busy:
            self.output_entry.configure(state="disabled")
            self.save_as_button.configure(state="disabled")
            self.include_subfolders_check.configure(state="disabled")
            self.header_style_combo.configure(state="disabled")
            return

        self._on_header_option_changed()

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

    def _on_header_option_changed(self) -> None:
        if self.install_running or self.conversion_running:
            return
        state = "readonly" if self.include_header_var.get() else "disabled"
        self.header_style_combo.configure(state=state)

    def _on_header_style_changed(self, _event: object | None = None) -> None:
        index = self.header_style_combo.current()
        if 0 <= index < len(HEADER_ORDER):
            self.header_style_var.set(HEADER_ORDER[index])

    def _on_mode_changed(self, _event: object | None = None) -> None:
        index = self.mode_combo.current()
        if 0 <= index < len(MODE_ORDER):
            self.input_mode_var.set(MODE_ORDER[index])
        self._handle_mode_change(clear_selection=True)

    def _sync_combobox_displays(self) -> None:
        mode_key = MODE_KEYS.get(self.input_mode_var.get(), "mode.single")
        self.mode_display_var.set(t(mode_key))
        header_key = HEADER_KEYS.get(self.header_style_var.get(), "headerstyle.blockquote")
        self.header_style_display_var.set(t(header_key))

    def _on_language_changed(self, _event: object | None = None) -> None:
        if self.conversion_running or self.install_running:
            self.language_var.set(label_for_language(current_language()))
            return
        code = language_for_label(self.language_var.get())
        if code == current_language():
            return
        set_language(code)
        save_language(code)
        self._rebuild_ui()

    def _rebuild_ui(self) -> None:
        saved_log = self.log_text.get("1.0", "end-1c")
        progress_value = float(self.progress_bar.cget("value"))
        progress_max = float(self.progress_bar.cget("maximum"))

        if self._main_frame is not None:
            self._main_frame.destroy()

        self._build_ui()

        if saved_log.strip():
            self.log_text.configure(state="normal")
            self.log_text.insert("1.0", saved_log + "\n")
            self.log_text.see("end")
            self.log_text.configure(state="disabled")
        self.progress_bar.configure(value=progress_value, maximum=progress_max)

        self._handle_mode_change(clear_selection=False)
        self._setup_drag_and_drop()
        self._refresh_widget_states()

    def _handle_mode_change(self, clear_selection: bool) -> None:
        if clear_selection:
            self.single_input_path = None
            self.multiple_input_paths = []
            self.folder_input_path = None
            self.input_summary_var.set("")
            self.output_path_var.set("")

        mode = self.input_mode_var.get()
        if mode == MODE_SINGLE:
            self.select_button.configure(text=t("button.select_file"))
        elif mode == MODE_MULTIPLE:
            self.select_button.configure(text=t("button.select_files"))
        else:
            self.select_button.configure(text=t("button.select_folder"))

        self._sync_combobox_displays()
        self._refresh_widget_states()
        self._append_log(f"Input mode set to: {mode}")

    def _select_input(self) -> None:
        mode = self.input_mode_var.get()

        if mode == MODE_SINGLE:
            selected = filedialog.askopenfilename(
                title=t("filedialog.select_document"),
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
                title=t("filedialog.select_documents"),
                filetypes=FILE_DIALOG_TYPES,
            )
            if not selected:
                return

            self.single_input_path = None
            self.multiple_input_paths = [Path(item) for item in selected]
            self.folder_input_path = None
            file_count = len(self.multiple_input_paths)
            self.input_summary_var.set(t("input.files_selected", n=file_count))
            self.output_path_var.set("")
            self._append_log(f"Selected multiple files: {file_count} files")
        else:
            selected = filedialog.askdirectory(title=t("filedialog.select_folder"))
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
            title=t("filedialog.save_as"),
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
        self.status_var.set(t("status.ready"))
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

        message = t(
            "dialog.missing_deps.body",
            list=self.dependency_manager.format_dependency_list(missing),
        )
        if messagebox.askyesno(t("dialog.missing_deps.title"), message):
            self._start_dependency_installation(missing)
        else:
            self._append_log("Automatic dependency installation was skipped by the user.")

    def _check_or_install_dependencies(self) -> None:
        self._append_log("Dependency check requested by the user.")
        for line in self.dependency_manager.get_status_lines():
            self._append_log(line)

        missing = self.dependency_manager.get_missing_dependencies()
        if not missing:
            self.status_var.set(t("status.deps_all_installed"))
            messagebox.showinfo(t("dialog.deps.title"), t("dialog.deps.all_installed"))
            return

        message = t(
            "dialog.install_deps.body",
            list=self.dependency_manager.format_dependency_list(missing),
        )
        if messagebox.askyesno(t("dialog.install_deps.title"), message):
            self._start_dependency_installation(missing)
        else:
            self._append_log("Dependency installation canceled by the user.")

    def _start_dependency_installation(self, missing: list[Dependency]) -> None:
        if self.install_running or self.conversion_running:
            return

        self.install_running = True
        self.status_var.set(t("status.installing_deps"))
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
            self.status_var.set(t("status.deps_ready"))
            self._append_log(message)
            messagebox.showinfo(t("dialog.dep_install.title"), message)
        else:
            self.status_var.set(t("status.deps_warning"))
            self._append_log(message)
            messagebox.showwarning(t("dialog.dep_install.title"), message)

    def _get_conversion_options(self) -> ConversionOptions:
        enabled_extensions: set[str] = set()
        if self.pdf_enabled_var.get():
            enabled_extensions.add(".pdf")
        if self.docx_enabled_var.get():
            enabled_extensions.add(".docx")
        if self.pptx_enabled_var.get():
            enabled_extensions.add(".pptx")

        if not enabled_extensions:
            raise ValueError(t("err.no_format"))

        return ConversionOptions(
            include_metadata=self.include_metadata_var.get(),
            include_page_slide_separators=self.include_page_slide_separators_var.get(),
            detect_headings=self.detect_headings_var.get(),
            normalize_whitespace=self.normalize_whitespace_var.get(),
            optimize_for_ai=self.optimize_for_ai_var.get(),
            include_subfolders=self.include_subfolders_var.get(),
            overwrite_existing=self.overwrite_existing_var.get(),
            include_header=self.include_header_var.get(),
            include_toc=self.include_toc_var.get(),
            header_style=self.header_style_var.get(),
            extract_images=self.extract_images_var.get(),
            enable_ocr=self.enable_ocr_var.get(),
            enabled_extensions=enabled_extensions,
        )

    def _start_conversion(self) -> None:
        if self.install_running or self.conversion_running:
            return

        try:
            options = self._get_conversion_options()
            jobs, scan_summary = self._build_conversion_jobs(options)
        except _InputSelectionError as exc:
            message = str(exc)
            self._append_log(message)
            self.status_var.set(message)
            messagebox.showwarning(t("dialog.no_input.title"), message)
            return
        except ValueError as exc:
            message = str(exc)
            self._append_log(message)
            self.status_var.set(message)
            return

        if not jobs:
            message = str(scan_summary.get("warning_message") or t("warn.no_files_ready"))
            self._append_log(message)
            self.status_var.set(message)
            messagebox.showwarning(t("dialog.no_files.title"), message)
            return

        self.conversion_running = True
        self.cancel_event.clear()
        self.progress_bar.configure(value=0, maximum=max(len(jobs), 1))
        self.status_var.set(t("status.converting_init", total=len(jobs)))
        self._refresh_widget_states()
        self._append_log("Conversion started.")
        self._append_log(f"Total jobs created: {len(jobs)}")

        thread = threading.Thread(
            target=self._convert_jobs_in_background,
            args=(jobs, options, scan_summary),
            daemon=True,
        )
        thread.start()

    def _cancel_conversion(self) -> None:
        if not self.conversion_running:
            return
        self.cancel_event.set()
        self.cancel_button.configure(state="disabled")
        self.status_var.set(t("status.canceling"))
        self._append_log("Cancel requested. Finishing the current file before stopping.")

    def _open_output_folder(self) -> None:
        folders = [folder for folder in self.last_output_folders if folder.exists()]
        if not folders:
            messagebox.showinfo(t("dialog.open_output.title"), t("dialog.open_output.none"))
            return

        target = folders[0]
        try:
            if sys.platform.startswith("win"):
                os.startfile(str(target))  # type: ignore[attr-defined]
            elif sys.platform == "darwin":
                subprocess.Popen(["open", str(target)])
            else:
                subprocess.Popen(["xdg-open", str(target)])
            self._append_log(f"Opened output folder: {target}")
        except Exception as exc:
            messagebox.showerror(t("dialog.open_output.title"), t("dialog.open_output.error", error=exc))

    def _export_log(self) -> None:
        log_content = self.log_text.get("1.0", "end").strip()
        if not log_content:
            messagebox.showinfo(t("dialog.export_log.title"), t("dialog.export_log.empty"))
            return

        selected = filedialog.asksaveasfilename(
            title=t("filedialog.export_log"),
            defaultextension=".txt",
            initialfile="doc2md_log.txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
        )
        if not selected:
            return

        try:
            Path(selected).write_text(log_content + "\n", encoding="utf-8")
            self._append_log(f"Log exported to: {selected}")
        except Exception as exc:
            messagebox.showerror(t("dialog.export_log.title"), t("dialog.export_log.error", error=exc))

    def _setup_drag_and_drop(self) -> None:
        """Enable drag-and-drop of files/folders onto the input field when available."""
        if not hasattr(self, "_dnd_enabled"):
            self._dnd_enabled = enable_drag_and_drop(self)
            if not self._dnd_enabled:
                self._append_log("Drag and drop is not available. Install the 'dnd' extra to enable it.")

        if not self._dnd_enabled:
            return

        registered = register_drop_target(self.input_display, self._handle_dropped_paths)
        if registered and not getattr(self, "_dnd_logged", False):
            self._append_log("Drag and drop enabled: drop files or a folder onto the input field.")
            self._dnd_logged = True

    def _handle_dropped_paths(self, raw_paths: list[str]) -> None:
        if self.install_running or self.conversion_running:
            return

        paths = [Path(item) for item in raw_paths if item]
        if not paths:
            return

        directories = [path for path in paths if path.is_dir()]
        files = [path for path in paths if path.is_file()]

        if directories:
            self.input_mode_var.set(MODE_FOLDER)
            self._handle_mode_change(clear_selection=True)
            self.folder_input_path = directories[0]
            self.input_summary_var.set(str(self.folder_input_path))
            self._append_log(f"Folder dropped: {self.folder_input_path}")
        elif len(files) == 1:
            self.input_mode_var.set(MODE_SINGLE)
            self._handle_mode_change(clear_selection=True)
            self.single_input_path = files[0]
            self.input_summary_var.set(str(self.single_input_path))
            self.output_path_var.set(str(self.single_input_path.with_suffix(".md")))
            self._append_log(f"File dropped: {self.single_input_path}")
        elif files:
            self.input_mode_var.set(MODE_MULTIPLE)
            self._handle_mode_change(clear_selection=True)
            self.multiple_input_paths = files
            self.input_summary_var.set(t("input.files_selected", n=len(files)))
            self._append_log(f"Dropped {len(files)} files.")

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
                raise _InputSelectionError(t("err.select_file"))
            if not self.single_input_path.exists():
                raise ValueError(t("err.file_missing", path=self.single_input_path))

            total_files_found = 1
            extension = self.single_input_path.suffix.lower()
            if extension not in SUPPORTED_EXTENSIONS:
                raise ValueError(t("err.unsupported"))
            if extension not in options.enabled_extensions:
                raise ValueError(t("err.disabled_type"))

            output_value = self.output_path_var.get().strip()
            if not output_value:
                raise ValueError(t("err.no_output_path"))

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
                raise _InputSelectionError(t("err.select_files"))

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
                raise _InputSelectionError(t("err.select_folder"))
            if not self.folder_input_path.exists() or not self.folder_input_path.is_dir():
                raise ValueError(t("err.invalid_folder", path=self.folder_input_path))

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
                warning_message = t("warn.no_files_in_folder")
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
                warning_message = t("warn.no_supported_in_folder")
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
            warning_message = t("warn.no_jobs")
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
        selected_folder: Path | None = None,
        log_skip: bool = True,
    ) -> ConversionJob | None:
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
        canceled = False

        for index, job in enumerate(jobs, start=1):
            if self.cancel_event.is_set():
                canceled = True
                self._post_log(f"Conversion canceled before processing {job.input_path.name}.")
                break

            self._post_status(
                t("status.converting_file", index=index, total=total_jobs, name=job.input_path.name)
            )
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
                canceled=canceled,
            ),
        )

    def _conversion_finished(
        self,
        total_jobs: int,
        success_count: int,
        failed_count: int,
        scan_summary: dict[str, object],
        canceled: bool = False,
    ) -> None:
        self.conversion_running = False

        output_folders = scan_summary.get("output_folders", [])
        self.last_output_folders = [Path(folder) for folder in output_folders]
        self._refresh_widget_states()
        self.progress_bar.configure(value=max(total_jobs, 0), maximum=max(total_jobs, 1))

        skipped_files = int(scan_summary.get("skipped_files", 0))
        output_folder_text = (
            "\n".join(str(folder) for folder in output_folders) or t("summary.no_output")
        )

        summary_lines = [
            t("summary.total_found", n=scan_summary.get("total_files_found", 0)),
            t("summary.jobs_created", n=scan_summary.get("jobs_created", 0)),
            t("summary.succeeded", n=success_count),
            t("summary.failed", n=failed_count),
            t("summary.skipped", n=skipped_files),
            t("summary.output_header"),
            output_folder_text,
        ]
        summary_message = "\n".join(summary_lines)

        self._append_log("Conversion summary:")
        self._append_log(summary_message)

        if canceled:
            self.status_var.set(t("status.canceled", ok=success_count, failed=failed_count))
            messagebox.showwarning(t("dialog.canceled.title"), summary_message)
        elif success_count > 0:
            self.status_var.set(
                t("status.completed", ok=success_count, failed=failed_count, skipped=skipped_files)
            )
            messagebox.showinfo(t("dialog.completed.title"), summary_message)
        else:
            self.status_var.set(t("status.failed"))
            messagebox.showerror(t("dialog.failed.title"), summary_message)
