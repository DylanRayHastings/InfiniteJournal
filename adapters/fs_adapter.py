"""
Filesystem persistence: JSON pages & screenshots.
"""
import json
from core.interfaces import Engine
from core.models import Page, Stroke, Point

class FileSystemJournalRepository:
    def save_page(self, page: Page, path: str):
        data = [{ 'points': [ {'x': p.x, 'y': p.y, 'width': p.width} for p in s.points ] }
                for s in page.strokes]
        with open(path, 'w') as f:
            json.dump(data, f)

    def load_page(self, path: str) -> Page:
        page = Page()
        with open(path) as f:
            data = json.load(f)
        for s in data:
            stroke = page.new_stroke()
            for pt in s['points']:
                stroke.add_point(Point(pt['x'], pt['y'], pt['width']))
        return page

class ScreenshotExporter:
    def save(self, engine: Engine, path: str):
        # engine-specific screenshot impl
        pass
