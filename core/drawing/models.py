# core/drawing/models.py (FIXED type safety and validation)
"""Data models for drawing primitives, with FIXED type safety and comprehensive validation."""

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Tuple, Dict, Any, Optional, Union

from .config import validate_file_path
from .exceptions import InvalidColorError, PersistenceError

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Point:
    """A point in 3D space with drawing attributes and comprehensive validation.

    Attributes:
        x: X-coordinate (float, clamped to reasonable bounds)
        y: Y-coordinate (float, clamped to reasonable bounds)
        z: Z-coordinate (depth), defaults to 0.0
        width: Brush width at this point (int, clamped to valid range)
    """

    x: float
    y: float
    z: float = 0.0
    width: int = 1

    def __post_init__(self) -> None:
        """Validate and clamp point values to safe ranges."""
        # Use object.__setattr__ because dataclass is frozen
        object.__setattr__(self, 'x', max(-9999.0, min(9999.0, float(self.x))))
        object.__setattr__(self, 'y', max(-9999.0, min(9999.0, float(self.y))))
        object.__setattr__(self, 'z', max(-100.0, min(100.0, float(self.z))))
        object.__setattr__(self, 'width', max(1, min(200, int(self.width))))
        
        logger.debug("Point created: (%.1f, %.1f, %.1f) width=%d", self.x, self.y, self.z, self.width)

    def to_dict(self) -> Dict[str, Union[float, int]]:
        """Serialize this Point to a dict with type safety."""
        return {
            "x": float(self.x), 
            "y": float(self.y), 
            "z": float(self.z), 
            "width": int(self.width)
        }

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "Point":
        """Create a Point from a dict with comprehensive error handling.

        Args:
            data: Dictionary with keys 'x', 'y', optional 'z', 'width'.

        Returns:
            A new Point instance.

        Raises:
            KeyError: If required keys are missing.
            ValueError: If values cannot be converted to correct types.
        """
        try:
            x = data["x"]
            y = data["y"]
            z = data.get("z", 0.0)
            width = data.get("width", 1)
            
            # Additional type validation
            if not isinstance(x, (int, float)):
                raise ValueError(f"Point x must be numeric, got {type(x)}")
            if not isinstance(y, (int, float)):
                raise ValueError(f"Point y must be numeric, got {type(y)}")
            
            return Point(
                x=float(x),
                y=float(y),
                z=float(z),
                width=int(width) if isinstance(width, (int, float)) else 1,
            )
        except KeyError as e:
            logger.error("Missing required key in point data: %s", e)
            raise KeyError(f"Missing required point data: {e}")
        except (ValueError, TypeError) as e:
            logger.error("Invalid point data: %s", e)
            raise ValueError(f"Invalid point data: {e}")

    def distance_to(self, other: "Point") -> float:
        """Calculate Euclidean distance to another point."""
        try:
            dx = self.x - other.x
            dy = self.y - other.y
            dz = self.z - other.z
            return (dx * dx + dy * dy + dz * dz) ** 0.5
        except Exception as e:
            logger.error("Error calculating distance: %s", e)
            return float('inf')

    def is_valid(self) -> bool:
        """Check if this point has valid coordinates."""
        try:
            return (
                isinstance(self.x, (int, float)) and 
                isinstance(self.y, (int, float)) and
                isinstance(self.z, (int, float)) and
                isinstance(self.width, int) and
                -9999 <= self.x <= 9999 and
                -9999 <= self.y <= 9999 and
                -100 <= self.z <= 100 and
                1 <= self.width <= 200
            )
        except Exception:
            return False


@dataclass
class Stroke:
    """A sequence of Points sharing the same RGB color with enhanced validation.

    Attributes:
        color: RGB tuple, each 0–255 (validated and clamped)
        points: Ordered list of Point instances (with validation)
        width: Default width for this stroke (used for rendering optimization)
    """

    color: Tuple[int, int, int]
    points: List[Point] = field(default_factory=list)
    width: int = 3

    def __post_init__(self) -> None:
        """Validate stroke properties with comprehensive error handling."""
        try:
            # Validate and fix color
            if not isinstance(self.color, (tuple, list)) or len(self.color) != 3:
                logger.warning("Invalid color format: %r, using default white", self.color)
                self.color = (255, 255, 255)
            else:
                # Clamp color values
                r, g, b = self.color
                self.color = (
                    max(0, min(255, int(r))),
                    max(0, min(255, int(g))),
                    max(0, min(255, int(b)))
                )
            
            # Validate width
            if not isinstance(self.width, (int, float)):
                logger.warning("Invalid stroke width: %r, using default", self.width)
                self.width = 3
            else:
                self.width = max(1, min(200, int(self.width)))
            
            # Validate points list
            if not isinstance(self.points, list):
                logger.warning("Invalid points container: %r, creating new list", type(self.points))
                self.points = []
            
            # Validate individual points
            valid_points = []
            for i, point in enumerate(self.points):
                try:
                    if isinstance(point, Point) and point.is_valid():
                        valid_points.append(point)
                    else:
                        logger.warning("Invalid point at index %d: %r", i, point)
                except Exception as e:
                    logger.warning("Error validating point at index %d: %s", i, e)
            
            self.points = valid_points
            
            logger.debug("Stroke validated: color=%s, width=%d, points=%d", 
                        self.color, self.width, len(self.points))
                        
        except Exception as e:
            logger.error("Critical error in stroke validation: %s", e)
            # Set safe defaults
            self.color = (255, 255, 255)
            self.width = 3
            self.points = []

    def add_point(self, point: Point) -> None:
        """Append a Point to this Stroke with validation.

        Args:
            point: Point to append.
            
        Raises:
            ValueError: If point is invalid.
        """
        try:
            if not isinstance(point, Point):
                raise ValueError(f"Expected Point object, got {type(point)}")
            
            if not point.is_valid():
                raise ValueError(f"Invalid point data: {point}")
            
            self.points.append(point)
            
            # Update stroke width to match the point width for consistency
            if point.width != self.width:
                self.width = point.width
                logger.debug("Stroke width updated to match point: %d", self.width)
            
            logger.debug("Added Point to stroke %s: %s (width: %d)", 
                        self.color, point, point.width)
                        
        except Exception as e:
            logger.error("Error adding point to stroke: %s", e)
            raise ValueError(f"Failed to add point: {e}")

    def remove_point(self, index: int) -> bool:
        """Remove a point at the specified index.
        
        Args:
            index: Index of point to remove.
            
        Returns:
            True if point was removed, False otherwise.
        """
        try:
            if 0 <= index < len(self.points):
                removed_point = self.points.pop(index)
                logger.debug("Removed point at index %d: %s", index, removed_point)
                return True
            else:
                logger.warning("Invalid point index: %d (total: %d)", index, len(self.points))
                return False
        except Exception as e:
            logger.error("Error removing point at index %d: %s", index, e)
            return False

    def get_bounding_box(self) -> Optional[Tuple[float, float, float, float]]:
        """Get bounding box of this stroke (min_x, min_y, max_x, max_y)."""
        try:
            if not self.points:
                return None
            
            xs = [p.x for p in self.points]
            ys = [p.y for p in self.points]
            
            return (min(xs), min(ys), max(xs), max(ys))
        except Exception as e:
            logger.error("Error calculating bounding box: %s", e)
            return None

    def get_length(self) -> float:
        """Calculate total length of the stroke."""
        try:
            if len(self.points) < 2:
                return 0.0
            
            total_length = 0.0
            for i in range(1, len(self.points)):
                total_length += self.points[i-1].distance_to(self.points[i])
            
            return total_length
        except Exception as e:
            logger.error("Error calculating stroke length: %s", e)
            return 0.0

    def simplify(self, tolerance: float = 2.0) -> "Stroke":
        """Create a simplified version of this stroke with fewer points.
        
        Args:
            tolerance: Distance tolerance for point removal.
            
        Returns:
            New simplified Stroke instance.
        """
        try:
            if len(self.points) <= 2:
                return Stroke(color=self.color, points=self.points.copy(), width=self.width)
            
            # Simple Douglas-Peucker-style simplification
            simplified_points = [self.points[0]]  # Always keep first point
            
            for i in range(1, len(self.points) - 1):
                prev_point = simplified_points[-1]
                curr_point = self.points[i]
                next_point = self.points[i + 1]
                
                # Calculate perpendicular distance
                dist = self._perpendicular_distance(curr_point, prev_point, next_point)
                if dist > tolerance:
                    simplified_points.append(curr_point)
            
            simplified_points.append(self.points[-1])  # Always keep last point
            
            logger.debug("Simplified stroke from %d to %d points", 
                        len(self.points), len(simplified_points))
            
            return Stroke(color=self.color, points=simplified_points, width=self.width)
            
        except Exception as e:
            logger.error("Error simplifying stroke: %s", e)
            return self  # Return original on error

    def _perpendicular_distance(self, point: Point, line_start: Point, line_end: Point) -> float:
        """Calculate perpendicular distance from point to line segment."""
        try:
            # Vector from line_start to line_end
            dx = line_end.x - line_start.x
            dy = line_end.y - line_start.y
            
            if dx == 0 and dy == 0:
                # Line segment is a point
                return point.distance_to(line_start)
            
            # Calculate perpendicular distance
            t = ((point.x - line_start.x) * dx + (point.y - line_start.y) * dy) / (dx * dx + dy * dy)
            t = max(0, min(1, t))  # Clamp to line segment
            
            closest_x = line_start.x + t * dx
            closest_y = line_start.y + t * dy
            
            return ((point.x - closest_x) ** 2 + (point.y - closest_y) ** 2) ** 0.5
            
        except Exception as e:
            logger.error("Error calculating perpendicular distance: %s", e)
            return float('inf')

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this Stroke to a dict with comprehensive error handling."""
        try:
            return {
                "color": list(self.color),  # Convert tuple to list for JSON
                "width": int(self.width),
                "points": [pt.to_dict() for pt in self.points],
            }
        except Exception as e:
            logger.error("Error serializing stroke: %s", e)
            # Return minimal valid representation
            return {
                "color": [255, 255, 255],
                "width": 3,
                "points": []
            }

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "Stroke":
        """Create a Stroke from its dict representation with error handling.

        Args:
            data: Dict with 'color', 'width', and 'points'.

        Returns:
            A new Stroke instance.
            
        Raises:
            ValueError: If data is invalid.
        """
        try:
            # Validate required fields
            if not isinstance(data, dict):
                raise ValueError("Stroke data must be a dictionary")
            
            color_data = data.get("color", [255, 255, 255])
            width_data = data.get("width", 3)
            points_data = data.get("points", [])
            
            # Validate color
            if isinstance(color_data, (list, tuple)) and len(color_data) >= 3:
                color = tuple(color_data[:3])
            else:
                logger.warning("Invalid color in stroke data: %r", color_data)
                color = (255, 255, 255)
            
            # Create stroke
            stroke = Stroke(color=color, width=width_data)
            
            # Add points with error handling
            if isinstance(points_data, list):
                for i, pt_data in enumerate(points_data):
                    try:
                        point = Point.from_dict(pt_data)
                        stroke.add_point(point)
                    except Exception as e:
                        logger.warning("Skipping invalid point %d in stroke: %s", i, e)
                        continue
            else:
                logger.warning("Invalid points data in stroke: %r", points_data)
            
            logger.debug("Created stroke from dict: %d points, color=%s", 
                        len(stroke.points), stroke.color)
            
            return stroke
            
        except Exception as e:
            logger.error("Error creating stroke from dict: %s", e)
            # Return minimal valid stroke
            return Stroke(color=(255, 255, 255), width=3)


@dataclass
class Page:
    """A drawing page: collection of Strokes with enhanced management."""

    strokes: List[Stroke] = field(default_factory=list)

    def __post_init__(self) -> None:
        """Validate page data."""
        try:
            if not isinstance(self.strokes, list):
                logger.warning("Invalid strokes container: %r, creating new list", type(self.strokes))
                self.strokes = []
            
            # Validate existing strokes
            valid_strokes = []
            for i, stroke in enumerate(self.strokes):
                try:
                    if isinstance(stroke, Stroke):
                        valid_strokes.append(stroke)
                    else:
                        logger.warning("Invalid stroke at index %d: %r", i, type(stroke))
                except Exception as e:
                    logger.warning("Error validating stroke at index %d: %s", i, e)
            
            self.strokes = valid_strokes
            logger.debug("Page validated with %d strokes", len(self.strokes))
            
        except Exception as e:
            logger.error("Error validating page: %s", e)
            self.strokes = []

    def new_stroke(self, color: Tuple[int, int, int], width: int = 3) -> Stroke:
        """Start a new Stroke with the given color and width, add it to this Page.

        Args:
            color: RGB tuple.
            width: Default width for the stroke.

        Returns:
            The newly created Stroke.
            
        Raises:
            ValueError: If parameters are invalid.
        """
        try:
            stroke = Stroke(color=color, width=width)
            self.strokes.append(stroke)
            logger.info("Started new stroke with color %s, width %d", color, width)
            return stroke
        except Exception as e:
            logger.error("Error creating new stroke: %s", e)
            raise ValueError(f"Failed to create stroke: {e}")

    def remove_stroke(self, stroke: Stroke) -> bool:
        """Remove a stroke from this page.
        
        Args:
            stroke: Stroke to remove.
            
        Returns:
            True if stroke was removed, False if not found.
        """
        try:
            if stroke in self.strokes:
                self.strokes.remove(stroke)
                logger.info("Removed stroke with %d points", len(stroke.points))
                return True
            else:
                logger.warning("Stroke not found in page")
                return False
        except Exception as e:
            logger.error("Error removing stroke: %s", e)
            return False

    def clear(self) -> None:
        """Remove all strokes from this page."""
        try:
            stroke_count = len(self.strokes)
            self.strokes.clear()
            logger.info("Cleared page with %d strokes", stroke_count)
        except Exception as e:
            logger.error("Error clearing page: %s", e)
            self.strokes = []

    def get_bounding_box(self) -> Optional[Tuple[float, float, float, float]]:
        """Get bounding box of all strokes (min_x, min_y, max_x, max_y)."""
        try:
            if not self.strokes:
                return None
            
            all_boxes = [stroke.get_bounding_box() for stroke in self.strokes]
            valid_boxes = [box for box in all_boxes if box is not None]
            
            if not valid_boxes:
                return None
            
            min_x = min(box[0] for box in valid_boxes)
            min_y = min(box[1] for box in valid_boxes)
            max_x = max(box[2] for box in valid_boxes)
            max_y = max(box[3] for box in valid_boxes)
            
            return (min_x, min_y, max_x, max_y)
            
        except Exception as e:
            logger.error("Error calculating page bounding box: %s", e)
            return None

    def get_stroke_count(self) -> int:
        """Get the number of strokes on this page."""
        try:
            return len(self.strokes)
        except Exception as e:
            logger.error("Error getting stroke count: %s", e)
            return 0

    def get_point_count(self) -> int:
        """Get the total number of points across all strokes."""
        try:
            return sum(len(stroke.points) for stroke in self.strokes)
        except Exception as e:
            logger.error("Error getting point count: %s", e)
            return 0

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this Page to a dict."""
        try:
            return {"strokes": [s.to_dict() for s in self.strokes]}
        except Exception as e:
            logger.error("Error serializing page: %s", e)
            return {"strokes": []}

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "Page":
        """Create a Page from its dict form with comprehensive error handling.

        Args:
            data: Dict with key 'strokes'.

        Returns:
            A new Page instance.
        """
        try:
            page = Page()
            
            if not isinstance(data, dict):
                logger.warning("Invalid page data type: %r", type(data))
                return page
            
            strokes_data = data.get("strokes", [])
            if not isinstance(strokes_data, list):
                logger.warning("Invalid strokes data type: %r", type(strokes_data))
                return page
            
            for i, stroke_data in enumerate(strokes_data):
                try:
                    stroke = Stroke.from_dict(stroke_data)
                    page.strokes.append(stroke)
                except Exception as e:
                    logger.warning("Skipping invalid stroke %d: %s", i, e)
                    continue
            
            logger.debug("Created page from dict with %d strokes", len(page.strokes))
            return page
            
        except Exception as e:
            logger.error("Error creating page from dict: %s", e)
            return Page()  # Return empty page on error

    def save(self, file_path: Path) -> None:
        """Persist this Page as JSON to disk with comprehensive error handling.

        Args:
            file_path: Path where to write.

        Raises:
            PersistenceError: On any I/O or validation failure.
        """
        try:
            validate_file_path(file_path)
            
            # Create backup of existing file if it exists
            if file_path.exists():
                backup_path = file_path.with_suffix(file_path.suffix + ".backup")
                try:
                    backup_path.write_bytes(file_path.read_bytes())
                    logger.debug("Created backup: %s", backup_path)
                except Exception as backup_error:
                    logger.warning("Failed to create backup: %s", backup_error)
            
            # Serialize and write
            data = self.to_dict()
            with file_path.open("w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
                
            logger.info("Page saved to %s (%d strokes, %d points)", 
                       file_path, self.get_stroke_count(), self.get_point_count())
                       
        except Exception as e:
            logger.error("Error saving page to %s: %s", file_path, e)
            raise PersistenceError(f"Failed to save page: {e}")

    @staticmethod
    def load(file_path: Path) -> "Page":
        """Load a Page from a JSON file with comprehensive error handling.

        Args:
            file_path: Path to read from.

        Returns:
            The loaded Page.

        Raises:
            PersistenceError: On any I/O or parse failure.
        """
        try:
            if not file_path.exists():
                raise FileNotFoundError(f"Page file not found: {file_path}")
            
            with file_path.open("r", encoding="utf-8") as f:
                data = json.load(f)
                
            page = Page.from_dict(data)
            logger.info("Page loaded from %s (%d strokes, %d points)", 
                       file_path, page.get_stroke_count(), page.get_point_count())
            return page
            
        except json.JSONDecodeError as e:
            logger.error("Invalid JSON in page file %s: %s", file_path, e)
            raise PersistenceError(f"Invalid page file format: {e}")
        except Exception as e:
            logger.error("Error loading page from %s: %s", file_path, e)
            raise PersistenceError(f"Failed to load page: {e}")