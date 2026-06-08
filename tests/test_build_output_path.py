"""Unit tests for :func:`doc2md.converters.build_output_path`."""

from __future__ import annotations

from pathlib import Path

import pytest

from doc2md.converters import build_output_path
from doc2md.models import MODE_FOLDER, MODE_MULTIPLE, MODE_SINGLE, OUTPUT_FOLDER_NAME


class TestSingleMode:
    def test_uses_explicit_output_path(self, tmp_path: Path) -> None:
        source = tmp_path / "doc.pdf"
        explicit = tmp_path / "result.md"
        result = build_output_path(
            source_path=source,
            mode=MODE_SINGLE,
            overwrite_existing=True,
            explicit_output_path=explicit,
        )
        assert result == explicit

    def test_forces_md_suffix(self, tmp_path: Path) -> None:
        source = tmp_path / "doc.pdf"
        explicit = tmp_path / "result.txt"
        result = build_output_path(
            source_path=source,
            mode=MODE_SINGLE,
            overwrite_existing=True,
            explicit_output_path=explicit,
        )
        assert result.suffix == ".md"

    def test_missing_explicit_path_raises(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError, match="single-file output path"):
            build_output_path(
                source_path=tmp_path / "doc.pdf",
                mode=MODE_SINGLE,
                overwrite_existing=True,
            )


class TestMultipleMode:
    def test_outputs_into_converted_folder(self, tmp_path: Path) -> None:
        source = tmp_path / "doc.docx"
        result = build_output_path(
            source_path=source,
            mode=MODE_MULTIPLE,
            overwrite_existing=True,
        )
        assert result == tmp_path / OUTPUT_FOLDER_NAME / "doc.md"


class TestFolderMode:
    def test_preserves_relative_structure(self, tmp_path: Path) -> None:
        folder = tmp_path / "src"
        source = folder / "nested" / "doc.pptx"
        result = build_output_path(
            source_path=source,
            mode=MODE_FOLDER,
            overwrite_existing=True,
            selected_folder=folder,
        )
        assert result == folder / OUTPUT_FOLDER_NAME / "nested" / "doc.md"

    def test_missing_folder_raises(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError, match="selected folder is required"):
            build_output_path(
                source_path=tmp_path / "doc.pptx",
                mode=MODE_FOLDER,
                overwrite_existing=True,
            )


class TestOverwriteBehavior:
    def test_unique_path_when_not_overwriting(self, tmp_path: Path) -> None:
        source = tmp_path / "doc.docx"
        existing = tmp_path / OUTPUT_FOLDER_NAME / "doc.md"
        existing.parent.mkdir(parents=True, exist_ok=True)
        existing.write_text("x", encoding="utf-8")

        result = build_output_path(
            source_path=source,
            mode=MODE_MULTIPLE,
            overwrite_existing=False,
        )
        assert result == tmp_path / OUTPUT_FOLDER_NAME / "doc_1.md"


def test_unsupported_mode_raises(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="Unsupported mode"):
        build_output_path(
            source_path=tmp_path / "doc.pdf",
            mode="bogus",
            overwrite_existing=True,
        )
