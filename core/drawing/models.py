"""Data models for drawing primitives - PERFORMANCE OPTIMIZED

Optimizations: __slots__, reduced validation, faster operations, memory efficiency.
"""

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Tuple, Dict, Any, Optional, Union

from .config import validate_file_path
from .exceptions import InvalidColorError, PersistenceError

logger = logging.getLogger(__name__)

@dataclass(frozen=True, slots=True)
class Point:
    """A point in 3D space - OPTIMIZED with slots and minimal validation."""
    x: float
    y: float
    z: float = 0.0
    width: int = 1

    def __post_init__(self) -> None:
        """Fast validation and clamping."""
        # Use object.__setattr__ for frozen dataclass - fast clamp
        object.__setattr__(self, 'x', max(-9999.0, min(9999.0, float(self.x))))
        object.__setattr__(self, 'y', max(-9999.0, min(9999.0, float(self.y))))
        object.__setattr__(self, 'z', max(-100.0, min(100.0, float(self.z))))
        object.__setattr__(self, 'width', max(1, min(200, int(self.width))))

    def to_dict(self) -> Dict[str, Union[float, int]]:
        """Serialize - optimized."""
        return {"x": self.x, "y": self.y, "z": self.z, "width": self.width}

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "Point":
        """Create Point from dict - optimized with minimal validation."""
        return Point(
            x=float(data.get("x", 0)),
            y=float(data.get("y", 0)),
            z=float(data.get("z", 0.0)),
            width=int(data.get("width", 1))
        )

    def distance_to(self, other: "Point") -> float:
        """Calculate distance - optimized."""
        dx = self.x - other.x
        dy = self.y - other.y
        dz = self.z - other.z
        return (dx * dx + dy * dy + dz * dz) ** 0.5

    def is_valid(self) -> bool:
        """Fast validity check."""
        return (-9999 <= self.x <= 9999 and -9999 <= self.y <= 9999 and
                -100 <= self.z <= 100 and 1 <= self.width <= 200)


class Stroke:
    """A sequence of Points - OPTIMIZED with slots."""
    __slots__ = ('color', 'points', 'width', '_bbox_cache', '_length_cache')

    def __init__(self, color: Tuple[int, int, int], points: Optional[List[Point]] = None, width: int = 3):
        # Fast color validation and clamping
        if isinstance(color, (tuple, list)) and len(color) >= 3:
            self.color = (
                max(0, min(255, int(color[0]))),
                max(0, min(255, int(color[1]))),
                max(0, min(255, int(color[2])))
            )
        else:
            self.color = (255, 255, 255)
        
        self.points = points or []
        self.width = max(1, min(200, int(width)))
        
        # Caches for performance
        self._bbox_cache = None
        self._length_cache = None

    def add_point(self, point: Point) -> None:
        """Add point - optimized."""
        self.points.append(point)
        # Invalidate caches
        self._bbox_cache = None
        self._length_cache = None
        
        # Update stroke width for consistency
        if point.width != self.width:
            self.width = point.width

    def remove_point(self, index: int) -> bool:
        """Remove point - optimized."""
        if 0 <= index < len(self.points):
            self.points.pop(index)
            self._bbox_cache = None
            self._length_cache = None
            return True
        return False

    def get_bounding_box(self) -> Optional[Tuple[float, float, float, float]]:
        """Get bounding box - cached for performance."""
        if self._bbox_cache is None and self.points:
            xs = [p.x for p in self.points]
            ys = [p.y for p in self.points]
            self._bbox_cache = (min(xs), min(ys), max(xs), max(ys))
        return self._bbox_cache

    def get_length(self) -> float:
        """Calculate stroke length - cached."""
        if self._length_cache is None:
            if len(self.points) < 2:
                self._length_cache = 0.0
            else:
                total = 0.0
                for i in range(1, len(self.points)):
                    total += self.points[i-1].distance_to(self.points[i])
                self._length_cache = total
        return self._length_cache

    def simplify(self, tolerance: float = 2.0) -> "Stroke":
        """Simplify stroke - optimized algorithm."""
        if len(self.points) <= 2:
            return Stroke(color=self.color, points=self.points[:], width=self.width)
        
        # Fast simplification
        simplified_points = [self.points[0]]
        
        for i in range(1, len(self.points) - 1):
            prev_point = simplified_points[-1]
            curr_point = self.points[i]
            
            # Simple distance check
            dx = curr_point.x - prev_point.x
            dy = curr_point.y - prev_point.y
            dist_sq = dx * dx + dy * dy
            
            if dist_sq > tolerance * tolerance:
                simplified_points.append(curr_point)
        
        simplified_points.append(self.points[-1])
        return Stroke(color=self.color, points=simplified_points, width=self.width)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize - optimized."""
        return {
            "color": list(self.color),
            "width": self.width,
            "points": [pt.to_dict() for pt in self.points],
        }

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "Stroke":
        """Create Stroke from dict - optimized."""
        color_data = data.get("color", [255, 255, 255])
        color = tuple(color_data[:3]) if len(color_data) >= 3 else (255, 255, 255)
        
        stroke = Stroke(color=color, width=data.get("width", 3))
        
        # Fast point creation
        points_data = data.get("points", [])
        if isinstance(points_data, list):
            stroke.points = [Point.from_dict(pt_data) for pt_data in points_data]
        
        return stroke


class Page:
    """A drawing page - OPTIMIZED with slots."""
    __slots__ = ('strokes', '_stroke_count_cache')

    def __init__(self, strokes: Optional[List[Stroke]] = None):
        self.strokes = strokes or []
        self._stroke_count_cache = None

    def new_stroke(self, color: Tuple[int, int, int], width: int = 3) -> Stroke:
        """Create new stroke - optimized."""
        stroke = Stroke(color=color, width=width)
        self.strokes.append(stroke)
        self._stroke_count_cache = None
        return stroke

    def remove_stroke(self, stroke: Stroke) -> bool:
        """Remove stroke - optimized."""
        try:
            self.strokes.remove(stroke)
            self._stroke_count_cache = None
            return True
        except ValueError:
            return False

    def clear(self) -> None:
        """Clear page - optimized."""
        self.strokes.clear()
        self._stroke_count_cache = None

    def get_bounding_box(self) -> Optional[Tuple[float, float, float, float]]:
        """Get page bounding box - optimized."""
        if not self.strokes:
            return None
        
        all_boxes = [stroke.get_bounding_box() for stroke in self.strokes]
        valid_boxes = [box for box in all_boxes if box is not None]
        
        if not valid_boxes:
            return None
        
        # Fast min/max calculation
        min_x = min(box[0] for box in valid_boxes)
        min_y = min(box[1] for box in valid_boxes)
        max_x = max(box[2] for box in valid_boxes)
        max_y = max(box[3] for box in valid_boxes)
        
        return (min_x, min_y, max_x, max_y)

    def get_stroke_count(self) -> int:
        """Get stroke count - cached."""
        if self._stroke_count_cache is None:
            self._stroke_count_cache = len(self.strokes)
        return self._stroke_count_cache

    def get_point_count(self) -> int:
        """Get total point count - optimized."""
        return sum(len(stroke.points) for stroke in self.strokes)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize - optimized."""
        return {"strokes": [s.to_dict() for s in self.strokes]}

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "Page":
        """Create Page from dict - optimized."""
        page = Page()
        
        strokes_data = data.get("strokes", [])
        if isinstance(strokes_data, list):
            page.strokes = [Stroke.from_dict(stroke_data) for stroke_data in strokes_data]
        
        return page

    def save(self, file_path: Path) -> None:
        """Save page - optimized with minimal validation."""
        validate_file_path(file_path)
        
        # Create backup if file exists
        if file_path.exists():
            backup_path = file_path.with_suffix(file_path.suffix + ".backup")
            try:
                backup_path.write_bytes(file_path.read_bytes())
            except Exception:
                pass  # Don't fail on backup creation
        
        # Write file
        data = self.to_dict()
        with file_path.open("w", encoding="utf-8") as f:
            json.dump(data, f, separators=(',', ':'))  # Compact JSON

    @staticmethod
    def load(file_path: Path) -> "Page":
        """Load page - optimized."""
        if not file_path.exists():
            raise PersistenceError(f"Page file not found: {file_path}")
        
        try:
            with file_path.open("r", encoding="utf-8") as f:
                data = json.load(f)
            return Page.from_dict(data)
        except json.JSONDecodeError as e:
            raise PersistenceError(f"Invalid page file format: {e}")
        except Exception as e:
            raise PersistenceError(f"Failed to load page: {e}")