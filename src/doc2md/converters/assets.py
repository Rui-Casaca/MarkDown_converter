"""Helpers for exporting embedded images alongside the generated Markdown."""

from __future__ import annotations

from pathlib import Path

_CONTENT_TYPE_EXTENSIONS = {
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/jpg": ".jpg",
    "image/gif": ".gif",
    "image/bmp": ".bmp",
    "image/tiff": ".tiff",
    "image/webp": ".webp",
    "image/x-emf": ".emf",
    "image/x-wmf": ".wmf",
}


def normalize_extension(value: str) -> str:
    """Return a lower-case, dot-prefixed image extension, defaulting to ``.png``."""
    ext = (value or "").strip().lower()
    if not ext:
        return ".png"
    if not ext.startswith("."):
        ext = f".{ext}"
    if ext == ".jpeg":
        ext = ".jpg"
    return ext


def extension_from_content_type(content_type: str) -> str:
    """Map an image MIME type to a file extension, defaulting to ``.png``."""
    return _CONTENT_TYPE_EXTENSIONS.get((content_type or "").strip().lower(), ".png")


def extension_from_name(name: str) -> str:
    """Derive an extension from an embedded image name, defaulting to ``.png``."""
    suffix = Path(name or "").suffix
    return normalize_extension(suffix) if suffix else ".png"


def image_markdown(relative_path: str, alt: str = "") -> str:
    """Build a Markdown image reference."""
    return f"![{alt}]({relative_path})"


class AssetWriter:
    """Writes extracted images into a sidecar ``<name>_assets`` folder."""

    def __init__(self, output_path: Path) -> None:
        self.assets_dir = output_path.with_name(f"{output_path.stem}_assets")
        self.folder_name = self.assets_dir.name
        self._index = 0

    def save_image(self, data: bytes | None, extension: str) -> str | None:
        """Persist image ``data`` and return its Markdown-relative path, or None."""
        if not data:
            return None

        self._index += 1
        filename = f"image_{self._index}{normalize_extension(extension)}"
        self.assets_dir.mkdir(parents=True, exist_ok=True)
        (self.assets_dir / filename).write_bytes(data)
        return f"{self.folder_name}/{filename}"
