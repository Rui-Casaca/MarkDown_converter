"""Optional OCR support for scanned PDF pages using pytesseract."""

from __future__ import annotations

import importlib
from typing import Any


class OcrEngine:
    """Thin wrapper around pytesseract that degrades gracefully when unavailable."""

    def __init__(self) -> None:
        self._pytesseract: Any = None
        self._available: bool | None = None

    def is_available(self) -> bool:
        """Return True only when pytesseract and the Tesseract binary are usable."""
        if self._available is not None:
            return self._available

        try:
            pytesseract = importlib.import_module("pytesseract")
            pytesseract.get_tesseract_version()
            self._pytesseract = pytesseract
            self._available = True
        except Exception:
            self._pytesseract = None
            self._available = False

        return self._available

    def image_to_text(self, image: Any) -> str:
        """Run OCR on a PIL image, returning recognized text or an empty string."""
        if image is None or not self.is_available():
            return ""

        try:
            return (self._pytesseract.image_to_string(image) or "").strip()
        except Exception:
            return ""
