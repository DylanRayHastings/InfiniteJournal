import json
from core.models import Point, Stroke
from pathlib import Path

class CanvasDatabase:
    def __init__(self, file_path='canvas_state.json'):
        self.file_path = Path(file_path)
        self.entries = []

    def add_stroke(self, stroke: Stroke):
        entry = {
            "type": "stroke",
            "color": stroke.color,
            "points": [
                {"x": p.x, "y": p.y, "z": getattr(p, 'z', 0), "width": p.width}
                for p in stroke.points
            ]
        }
        self.entries.append(entry)
        self.save()

    def save(self):
        with self.file_path.open('w') as f:
            json.dump(self.entries, f, indent=2)
