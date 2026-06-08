"""Optional drag-and-drop support backed by tkinterdnd2.

The whole feature degrades gracefully: if ``tkinterdnd2`` (and its underlying
tkdnd Tcl package) is not available, the helpers simply report that drag and
drop could not be enabled and the application keeps working without it.
"""

from __future__ import annotations

import importlib
from collections.abc import Callable
from typing import Any


def enable_drag_and_drop(window: Any) -> bool:
    """Initialise tkdnd on ``window``. Returns True when drag and drop is usable."""
    try:
        tkinterdnd2 = importlib.import_module("tkinterdnd2")
        window.TkdndVersion = tkinterdnd2.TkinterDnD._require(window)
        return True
    except Exception:
        return False


def register_drop_target(widget: Any, on_paths: Callable[[list[str]], None]) -> bool:
    """Register ``widget`` so dropped files invoke ``on_paths``. Returns success."""
    try:
        tkinterdnd2 = importlib.import_module("tkinterdnd2")
    except Exception:
        return False

    try:
        widget.drop_target_register(tkinterdnd2.DND_FILES)
        widget.dnd_bind("<<Drop>>", lambda event: on_paths(parse_drop_data(widget, event.data)))
        return True
    except Exception:
        return False


def parse_drop_data(widget: Any, data: str) -> list[str]:
    """Split the platform-specific drop payload into a list of file paths."""
    if not data:
        return []
    try:
        return [str(item) for item in widget.tk.splitlist(data)]
    except Exception:
        return [data]
