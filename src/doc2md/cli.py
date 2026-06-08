"""Command-line entry point that launches the doc2md graphical application."""

from __future__ import annotations

from .ui.app import DocumentToMarkdownApp


def main() -> int:
    app = DocumentToMarkdownApp()
    app.mainloop()
    return 0
