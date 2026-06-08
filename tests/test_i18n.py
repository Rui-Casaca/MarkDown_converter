"""Tests for the i18n translator and catalogs."""

from __future__ import annotations

from doc2md.i18n import (
    CATALOGS,
    DEFAULT_LANGUAGE,
    LANGUAGES,
    Translator,
    label_for_language,
    language_for_label,
)


class TestTranslatorLookup:
    def test_default_language_is_english(self) -> None:
        assert Translator().language == "en"

    def test_returns_translation_for_known_key(self) -> None:
        translator = Translator("pt")
        assert translator.gettext("button.convert") == "Converter"

    def test_english_lookup(self) -> None:
        translator = Translator("en")
        assert translator.gettext("button.convert") == "Convert"

    def test_unknown_key_returns_key(self) -> None:
        translator = Translator("en")
        assert translator.gettext("does.not.exist") == "does.not.exist"

    def test_unknown_language_falls_back_to_default(self) -> None:
        translator = Translator("zz")
        assert translator.language == DEFAULT_LANGUAGE


class TestTranslatorFormatting:
    def test_formats_named_placeholders(self) -> None:
        translator = Translator("en")
        result = translator.gettext("status.converting_file", index=2, total=5, name="a.pdf")
        assert result == "Converting 2 of 5: a.pdf"

    def test_portuguese_formatting(self) -> None:
        translator = Translator("pt")
        result = translator.gettext("summary.succeeded", n=3)
        assert result == "Convertidos com sucesso: 3"

    def test_missing_placeholder_returns_template(self) -> None:
        translator = Translator("en")
        # Missing kwargs should not raise; the raw template is returned instead.
        result = translator.gettext("status.converting_file", index=1)
        assert "{total}" in result


class TestSetLanguage:
    def test_switches_language(self) -> None:
        translator = Translator("en")
        translator.set_language("pt")
        assert translator.language == "pt"
        assert translator.gettext("button.cancel") == "Cancelar"

    def test_ignores_unknown_language(self) -> None:
        translator = Translator("en")
        translator.set_language("zz")
        assert translator.language == "en"


class TestLanguageLabels:
    def test_label_for_language(self) -> None:
        assert label_for_language("pt") == "Português"
        assert label_for_language("en") == "English"

    def test_label_for_unknown_returns_code(self) -> None:
        assert label_for_language("zz") == "zz"

    def test_language_for_label_roundtrip(self) -> None:
        for code in LANGUAGES:
            assert language_for_label(label_for_language(code)) == code

    def test_language_for_unknown_label_returns_default(self) -> None:
        assert language_for_label("Klingon") == DEFAULT_LANGUAGE


class TestCatalogParity:
    def test_all_languages_share_the_same_keys(self) -> None:
        english_keys = set(CATALOGS["en"])
        for language, catalog in CATALOGS.items():
            assert set(catalog) == english_keys, f"Catalog '{language}' has mismatched keys"

    def test_no_empty_translations(self) -> None:
        for language, catalog in CATALOGS.items():
            for key, value in catalog.items():
                assert value.strip(), f"Empty translation for '{key}' in '{language}'"
