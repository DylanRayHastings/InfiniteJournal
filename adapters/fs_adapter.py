"""
Filesystem persistence: JSON pages & screenshots.
"""
import json
import logging
from pathlib import Path

from core.drawing.models import Page, Point

logger = logging.getLogger(__name__)


class FileSystemJournalRepository:
    """
    Stores and retrieves journal pages as JSON files on disk.

    Provides a `save(page, page_id)` method for strokes-based services.
    """
    def __init__(self, base_path: Path):
        """Initialize with a base directory. Creates it if necessary."""
        self.set_base_path(base_path)

    def set_base_path(self, path: Path) -> None:
        if not path.exists():
            try:
                path.mkdir(parents=True, exist_ok=True)
            except OSError as e:
                raise RuntimeError(f"Cannot create journal directory '{path}': {e}")
        if not path.is_dir():
            raise RuntimeError(f"Journal path '{path}' exists but is not a directory")
        self._base_path = path
        logger.debug(f"Journal base path set to: {path}")

    def _ensure_ready(self):
        if not hasattr(self, '_base_path') or self._base_path is None:
            raise RuntimeError(
                "FileSystemJournalRepository used before base_path was configured."
            )

    def save_page(self, page: Page, page_id: str) -> None:
        """Save a Page object as JSON under the given page_id."""
        self._ensure_ready()
        data = [
            {'points': [{'x': p.x, 'y': p.y, 'width': p.width} for p in s.points]}
            for s in page.strokes
        ]
        target = self._base_path / f"{page_id}.json"
        with target.open('w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
        logger.info(f"Saved page '%s' to %s", page_id, target)

    def load_page(self, page_id: str) -> Page:
        """Load a Page object from JSON stored under the given page_id."""
        self._ensure_ready()
        target = self._base_path / f"{page_id}.json"
        if not target.exists():
            raise FileNotFoundError(f"No journal file at {target}")
        page = Page()
        with target.open('r', encoding='utf-8') as f:
            data = json.load(f)
        for s in data:
            stroke = page.new_stroke()
            for pt in s.get('points', []):
                stroke.add_point(Point(pt['x'], pt['y'], pt.get('width', 1)))
        logger.info(f"Loaded page '%s' from %s", page_id, target)
        return page

    # Compatibility methods for service interface
    def save(self, *args, **kwargs) -> None:
        """Alias to save_page for compatibility with stroke-based services."""
        return self.save_page(*args, **kwargs)

    def close(self) -> None:
        """Close the repository. No-op for filesystem storage."""
        logger.debug("FileSystemJournalRepository.close() called; no resources to release.")


class ScreenshotExporter:
    """
    Exports renderer screenshots into files on disk.
    """
    def __init__(self, base_path: Path):
        self.set_base_path(base_path)

    def set_base_path(self, path: Path) -> None:
        if not path.exists():
            try:
                path.mkdir(parents=True, exist_ok=True)
            except OSError as e:
                raise RuntimeError(f"Cannot create screenshots directory '{path}': {e}")
        if not path.is_dir():
            raise RuntimeError(f"Screenshots path '{path}' exists but is not a directory")
        self._base_path = path
        logger.debug(f"Screenshots base path set to: {path}")

    def export(self, image, name: str) -> None:
        """Save a screenshot image under the given name."""
        if not hasattr(self, '_base_path') or self._base_path is None:
            raise RuntimeError(
                "ScreenshotExporter used before base_path was configured."
            )
        filename = self._base_path / f"{name}.png"
        try:
            image.save(str(filename))
            logger.info(f"Screenshot saved to %s", filename)
        except Exception as e:
            logger.exception("Failed to export screenshot '%s': %s", filename, e)
            raise
