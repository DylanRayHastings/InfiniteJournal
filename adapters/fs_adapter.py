"""
Filesystem persistence: JSON pages & screenshots.
"""
import json
from pathlib import Path
import logging

from core.interfaces import Engine
from core.models import Page, Point

logger = logging.getLogger(__name__)

class FileSystemJournalRepository:
    """
    Stores and retrieves journal pages as JSON files on disk.
    """
    def __init__(self, base_path: Path):
        """
        Initialize with a base directory. Creates it if necessary.
        """
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
        self._ensure_ready()
        data = [
            {'points': [{'x': p.x, 'y': p.y, 'width': p.width} for p in s.points]}
            for s in page.strokes
        ]
        target = self._base_path / f"{page_id}.json"
        with open(target, 'w') as f:
            json.dump(data, f)

    def load_page(self, page_id: str) -> Page:
        self._ensure_ready()
        target = self._base_path / f"{page_id}.json"
        if not target.exists():
            raise FileNotFoundError(f"No journal file at {target}")
        page = Page()
        with open(target) as f:
            data = json.load(f)
        for s in data:
            stroke = page.new_stroke()
            for pt in s['points']:
                stroke.add_point(Point(pt['x'], pt['y'], pt['width']))
        return page

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
        logging.getLogger(__name__).debug(f"Screenshots base path set to: {path}")

    def export(self, image, name: str) -> None:
        if not hasattr(self, '_base_path') or self._base_path is None:
            raise RuntimeError(
                "ScreenshotExporter used before base_path was configured."
            )
        filename = self._base_path / f"{name}.png"
        image.save(str(filename))
