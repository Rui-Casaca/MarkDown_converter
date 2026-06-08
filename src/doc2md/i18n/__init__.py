"""Lightweight runtime internationalization for the doc2md GUI.

A single process-wide :class:`Translator` holds the active language. UI code
calls :func:`t` to look up a key, falling back to English and then to the key
itself so partial catalogs never crash the interface.
"""

from __future__ import annotations

from .en import CATALOG as EN_CATALOG
from .pt import CATALOG as PT_CATALOG

DEFAULT_LANGUAGE = "en"
CATALOGS: dict[str, dict[str, str]] = {
    "en": EN_CATALOG,
    "pt": PT_CATALOG,
}
LANGUAGES: tuple[str, ...] = ("en", "pt")
LANGUAGE_LABELS: dict[str, str] = {
    "en": "English",
    "pt": "Português",
}


class Translator:
    """Resolves message keys for the currently selected language."""

    def __init__(self, language: str = DEFAULT_LANGUAGE) -> None:
        self._language = language if language in CATALOGS else DEFAULT_LANGUAGE

    @property
    def language(self) -> str:
        return self._language

    def set_language(self, language: str) -> None:
        if language in CATALOGS:
            self._language = language

    def gettext(self, key: str, **kwargs: object) -> str:
        catalog = CATALOGS.get(self._language, {})
        template = catalog.get(key)
        if template is None:
            template = CATALOGS[DEFAULT_LANGUAGE].get(key, key)
        if kwargs:
            try:
                return template.format(**kwargs)
            except (KeyError, IndexError, ValueError):
                return template
        return template


_translator = Translator()


def get_translator() -> Translator:
    return _translator


def t(key: str, **kwargs: object) -> str:
    return _translator.gettext(key, **kwargs)


def set_language(language: str) -> None:
    _translator.set_language(language)


def current_language() -> str:
    return _translator.language


def label_for_language(code: str) -> str:
    return LANGUAGE_LABELS.get(code, code)


def language_for_label(label: str) -> str:
    for code, name in LANGUAGE_LABELS.items():
        if name == label:
            return code
    return DEFAULT_LANGUAGE
