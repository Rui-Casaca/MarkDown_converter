"""Tests for image asset export and OCR helpers."""

from __future__ import annotations

from pathlib import Path

from doc2md.converters.assets import (
    AssetWriter,
    extension_from_content_type,
    extension_from_name,
    image_markdown,
    normalize_extension,
)
from doc2md.converters.ocr import OcrEngine


class TestNormalizeExtension:
    def test_adds_leading_dot(self) -> None:
        assert normalize_extension("png") == ".png"

    def test_lowercases(self) -> None:
        assert normalize_extension(".PNG") == ".png"

    def test_jpeg_maps_to_jpg(self) -> None:
        assert normalize_extension("jpeg") == ".jpg"

    def test_empty_defaults_to_png(self) -> None:
        assert normalize_extension("") == ".png"


class TestExtensionFromContentType:
    def test_known_types(self) -> None:
        assert extension_from_content_type("image/png") == ".png"
        assert extension_from_content_type("image/jpeg") == ".jpg"
        assert extension_from_content_type("image/gif") == ".gif"

    def test_unknown_defaults_to_png(self) -> None:
        assert extension_from_content_type("application/octet-stream") == ".png"

    def test_case_insensitive(self) -> None:
        assert extension_from_content_type("IMAGE/PNG") == ".png"


class TestExtensionFromName:
    def test_uses_suffix(self) -> None:
        assert extension_from_name("Im1.jpeg") == ".jpg"

    def test_no_suffix_defaults_to_png(self) -> None:
        assert extension_from_name("image") == ".png"


class TestImageMarkdown:
    def test_default_alt(self) -> None:
        assert image_markdown("assets/a.png") == "![](assets/a.png)"

    def test_custom_alt(self) -> None:
        assert image_markdown("assets/a.png", "Figure 1") == "![Figure 1](assets/a.png)"


class TestAssetWriter:
    def test_folder_name_from_output(self, tmp_path: Path) -> None:
        writer = AssetWriter(tmp_path / "report.md")
        assert writer.folder_name == "report_assets"

    def test_save_returns_relative_posix_path(self, tmp_path: Path) -> None:
        writer = AssetWriter(tmp_path / "report.md")
        result = writer.save_image(b"data", ".png")
        assert result == "report_assets/image_1.png"

    def test_save_writes_file(self, tmp_path: Path) -> None:
        writer = AssetWriter(tmp_path / "report.md")
        writer.save_image(b"binary", ".png")
        written = tmp_path / "report_assets" / "image_1.png"
        assert written.exists()
        assert written.read_bytes() == b"binary"

    def test_index_increments(self, tmp_path: Path) -> None:
        writer = AssetWriter(tmp_path / "report.md")
        assert writer.save_image(b"a", ".png") == "report_assets/image_1.png"
        assert writer.save_image(b"b", ".jpg") == "report_assets/image_2.jpg"

    def test_empty_data_returns_none(self, tmp_path: Path) -> None:
        writer = AssetWriter(tmp_path / "report.md")
        assert writer.save_image(b"", ".png") is None
        assert writer.save_image(None, ".png") is None

    def test_no_folder_created_until_first_save(self, tmp_path: Path) -> None:
        AssetWriter(tmp_path / "report.md")
        assert not (tmp_path / "report_assets").exists()


class _FakePytesseract:
    def __init__(self, text: str) -> None:
        self._text = text

    def get_tesseract_version(self) -> str:
        return "5.0.0"

    def image_to_string(self, image: object) -> str:
        return self._text


class TestOcrEngine:
    def test_unavailable_without_pytesseract(self) -> None:
        # pytesseract is not installed in the test environment.
        engine = OcrEngine()
        assert engine.is_available() is False

    def test_image_to_text_empty_when_unavailable(self) -> None:
        engine = OcrEngine()
        assert engine.image_to_text(object()) == ""

    def test_image_to_text_with_injected_backend(self) -> None:
        engine = OcrEngine()
        engine._available = True
        engine._pytesseract = _FakePytesseract("  recognized text  ")
        assert engine.image_to_text(object()) == "recognized text"

    def test_image_to_text_none_image(self) -> None:
        engine = OcrEngine()
        engine._available = True
        engine._pytesseract = _FakePytesseract("text")
        assert engine.image_to_text(None) == ""
