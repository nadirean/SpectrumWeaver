"""Tests for the bundled asset files."""

from pathlib import Path

ASSETS_DIR = Path(__file__).resolve().parent.parent / "src" / "assets"


class TestAssets:
    """Test cases for the asset files."""

    def test_icon_exists(self) -> None:
        assert (ASSETS_DIR / "icon.png").is_file()

    def test_icon_is_png(self) -> None:
        data = (ASSETS_DIR / "icon.png").read_bytes()
        assert data.startswith(b"\x89PNG\r\n\x1a\n")

    def test_stylesheet_exists(self) -> None:
        assert (ASSETS_DIR / "styles.qss").is_file()

    def test_stylesheet_is_non_empty_text(self) -> None:
        text = (ASSETS_DIR / "styles.qss").read_text(encoding="utf-8")
        assert len(text.strip()) > 0
