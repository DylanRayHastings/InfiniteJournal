# core/coordinates/infinite_system.py (NEW FILE - Infinite coordinate system)
"""
Hierarchical Coordinate System for InfiniteJournal

Handles large-scale coordinates using grid cells and local offsets to prevent
overflow and precision loss at extreme zoom levels.

Architecture:
- World coordinates: Global position using cell + local offset
- Screen coordinates: Viewport-relative positions for rendering
- Automatic bounds checking and coordinate clamping
"""

import logging
import math
import threading
from typing import Tuple, List, Optional, Dict, Any
from dataclasses import dataclass
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)

# Constants for coordinate system
CELL_SIZE = 4096  # Size of each world cell in local units
MAX_CELLS = 16384  # Maximum cells in each direction (±16384)
MAX_LOCAL_COORD = CELL_SIZE - 1
MIN_LOCAL_COORD = 0
MAX_WORLD_COORD = MAX_CELLS * CELL_SIZE
MIN_WORLD_COORD = -MAX_CELLS * CELL_SIZE


class CoordinateError(Exception):
    """Raised when coordinate operations fail."""
    pass


@dataclass
class WorldCoordinate:
    """
    Hierarchical coordinate with cell and local offset.
    
    This allows handling extremely large coordinate spaces without
    precision loss or overflow issues.
    """
    cell_x: int = 0
    cell_y: int = 0
    local_x: float = 0.0
    local_y: float = 0.0
    
    def __post_init__(self):
        """Validate and normalize coordinates."""
        self._normalize()
        self._validate()
        
    def _normalize(self):
        """Normalize local coordinates to keep them within cell bounds."""
        try:
            # Handle x coordinate overflow
            if self.local_x >= CELL_SIZE:
                cell_offset = int(self.local_x // CELL_SIZE)
                self.cell_x += cell_offset
                self.local_x -= cell_offset * CELL_SIZE
            elif self.local_x < 0:
                cell_offset = int((-self.local_x - 1) // CELL_SIZE) + 1
                self.cell_x -= cell_offset
                self.local_x += cell_offset * CELL_SIZE
                
            # Handle y coordinate overflow
            if self.local_y >= CELL_SIZE:
                cell_offset = int(self.local_y // CELL_SIZE)
                self.cell_y += cell_offset
                self.local_y -= cell_offset * CELL_SIZE
            elif self.local_y < 0:
                cell_offset = int((-self.local_y - 1) // CELL_SIZE) + 1
                self.cell_y -= cell_offset
                self.local_y += cell_offset * CELL_SIZE
                
        except Exception as e:
            logger.error("Error normalizing coordinates: %s", e)
            self._reset_to_origin()
            
    def _validate(self):
        """Validate coordinates are within system bounds."""
        try:
            # Clamp cell coordinates
            self.cell_x = max(-MAX_CELLS, min(MAX_CELLS, self.cell_x))
            self.cell_y = max(-MAX_CELLS, min(MAX_CELLS, self.cell_y))
            
            # Clamp local coordinates
            self.local_x = max(0.0, min(float(CELL_SIZE - 1), self.local_x))
            self.local_y = max(0.0, min(float(CELL_SIZE - 1), self.local_y))
            
        except Exception as e:
            logger.error("Error validating coordinates: %s", e)
            self._reset_to_origin()
            
    def _reset_to_origin(self):
        """Reset to origin on critical errors."""
        self.cell_x = 0
        self.cell_y = 0
        self.local_x = 0.0
        self.local_y = 0.0
        
    def to_world_float(self) -> Tuple[float, float]:
        """Convert to world coordinates as floats."""
        try:
            world_x = float(self.cell_x * CELL_SIZE) + self.local_x
            world_y = float(self.cell_y * CELL_SIZE) + self.local_y
            return (world_x, world_y)
        except Exception as e:
            logger.error("Error converting to world coordinates: %s", e)
            return (0.0, 0.0)
            
    def to_world_int(self) -> Tuple[int, int]:
        """Convert to world coordinates as integers."""
        world_x, world_y = self.to_world_float()
        return (int(world_x), int(world_y))
        
    @classmethod
    def from_world(cls, world_x: float, world_y: float) -> 'WorldCoordinate':
        """Create WorldCoordinate from world position."""
        try:
            # Calculate cell coordinates
            cell_x = int(world_x // CELL_SIZE) if world_x >= 0 else int((world_x - CELL_SIZE + 1) // CELL_SIZE)
            cell_y = int(world_y // CELL_SIZE) if world_y >= 0 else int((world_y - CELL_SIZE + 1) // CELL_SIZE)
            
            # Calculate local coordinates
            local_x = world_x - cell_x * CELL_SIZE
            local_y = world_y - cell_y * CELL_SIZE
            
            return cls(cell_x, cell_y, local_x, local_y)
        except Exception as e:
            logger.error("Error creating WorldCoordinate from world position: %s", e)
            return cls(0, 0, 0.0, 0.0)
            
    def distance_to(self, other: 'WorldCoordinate') -> float:
        """Calculate distance to another world coordinate."""
        try:
            self_world = self.to_world_float()
            other_world = other.to_world_float()
            
            dx = self_world[0] - other_world[0]
            dy = self_world[1] - other_world[1]
            
            return math.sqrt(dx * dx + dy * dy)
        except Exception as e:
            logger.error("Error calculating distance: %s", e)
            return float('inf')
            
    def add_offset(self, dx: float, dy: float) -> 'WorldCoordinate':
        """Add offset and return new coordinate."""
        try:
            new_local_x = self.local_x + dx
            new_local_y = self.local_y + dy
            
            return WorldCoordinate(self.cell_x, self.cell_y, new_local_x, new_local_y)
        except Exception as e:
            logger.error("Error adding offset: %s", e)
            return WorldCoordinate(self.cell_x, self.cell_y, self.local_x, self.local_y)
            
    def is_in_same_cell(self, other: 'WorldCoordinate') -> bool:
        """Check if two coordinates are in the same cell."""
        return self.cell_x == other.cell_x and self.cell_y == other.cell_y
        
    def __str__(self) -> str:
        return f"Cell({self.cell_x}, {self.cell_y}) + Local({self.local_x:.2f}, {self.local_y:.2f})"


class Viewport:
    """
    Viewport for converting between world and screen coordinates.
    
    Handles panning, zooming, and coordinate transformation with
    proper bounds checking for infinite canvas.
    """
    
    def __init__(self, screen_width: int, screen_height: int):
        self.screen_width = screen_width
        self.screen_height = screen_height
        
        # Viewport state
        self.center = WorldCoordinate(0, 0, 0.0, 0.0)  # World center of viewport
        self.zoom_level = 1.0
        self.min_zoom = 0.01
        self.max_zoom = 100.0
        
        # Performance optimization
        self._transform_cache = {}
        self._cache_valid = False
        self._lock = threading.Lock()
        
    def pan(self, screen_dx: int, screen_dy: int) -> None:
        """Pan viewport by screen pixel amounts."""
        try:
            # Convert screen deltas to world deltas
            world_dx = screen_dx / self.zoom_level
            world_dy = screen_dy / self.zoom_level
            
            # Update center position
            self.center = self.center.add_offset(-world_dx, -world_dy)
            
            self._invalidate_cache()
            
            logger.debug("Viewport panned by screen(%d, %d) -> world(%.2f, %.2f)", 
                        screen_dx, screen_dy, -world_dx, -world_dy)
                        
        except Exception as e:
            logger.error("Error panning viewport: %s", e)
            
    def zoom(self, factor: float, screen_center: Tuple[int, int]) -> None:
        """Zoom viewport around screen center point."""
        try:
            # Clamp zoom level
            new_zoom = max(self.min_zoom, min(self.max_zoom, self.zoom_level * factor))
            
            if new_zoom == self.zoom_level:
                return  # No change needed
                
            # Convert screen center to world coordinates before zoom
            world_center = self.screen_to_world(screen_center[0], screen_center[1])
            
            # Apply zoom
            old_zoom = self.zoom_level
            self.zoom_level = new_zoom
            
            # Convert world center back to screen coordinates after zoom
            new_screen_center = self.world_to_screen_coord(world_center)
            
            # Adjust viewport center to keep zoom point stable
            screen_offset_x = new_screen_center[0] - screen_center[0]
            screen_offset_y = new_screen_center[1] - screen_center[1]
            
            self.pan(screen_offset_x, screen_offset_y)
            
            self._invalidate_cache()
            
            logger.debug("Viewport zoomed from %.3f to %.3f around screen(%d, %d)", 
                        old_zoom, new_zoom, screen_center[0], screen_center[1])
                        
        except Exception as e:
            logger.error("Error zooming viewport: %s", e)
            
    def screen_to_world(self, screen_x: int, screen_y: int) -> WorldCoordinate:
        """Convert screen coordinates to world coordinates."""
        try:
            # Screen center
            center_x = self.screen_width // 2
            center_y = self.screen_height // 2
            
            # Offset from screen center
            offset_x = (screen_x - center_x) / self.zoom_level
            offset_y = (screen_y - center_y) / self.zoom_level
            
            # Add offset to viewport center
            return self.center.add_offset(offset_x, offset_y)
            
        except Exception as e:
            logger.error("Error converting screen to world coordinates: %s", e)
            return WorldCoordinate(0, 0, 0.0, 0.0)
            
    def world_to_screen(self, world_x: float, world_y: float) -> Tuple[int, int]:
        """Convert world coordinates to screen coordinates."""
        try:
            # Convert to world coordinate
            world_coord = WorldCoordinate.from_world(world_x, world_y)
            return self.world_to_screen_coord(world_coord)
        except Exception as e:
            logger.error("Error converting world to screen coordinates: %s", e)
            return (self.screen_width // 2, self.screen_height // 2)
            
    def world_to_screen_coord(self, world_coord: WorldCoordinate) -> Tuple[int, int]:
        """Convert WorldCoordinate to screen coordinates."""
        try:
            # Get world positions
            center_world = self.center.to_world_float()
            coord_world = world_coord.to_world_float()
            
            # Calculate world offset from viewport center
            world_offset_x = coord_world[0] - center_world[0]
            world_offset_y = coord_world[1] - center_world[1]
            
            # Convert to screen offset
            screen_offset_x = world_offset_x * self.zoom_level
            screen_offset_y = world_offset_y * self.zoom_level
            
            # Calculate screen position
            screen_center_x = self.screen_width // 2
            screen_center_y = self.screen_height // 2
            
            screen_x = int(screen_center_x + screen_offset_x)
            screen_y = int(screen_center_y + screen_offset_y)
            
            return (screen_x, screen_y)
            
        except Exception as e:
            logger.error("Error converting WorldCoordinate to screen: %s", e)
            return (self.screen_width // 2, self.screen_height // 2)
            
    def is_visible(self, world_coord: WorldCoordinate, margin: int = 100) -> bool:
        """Check if world coordinate is visible in viewport."""
        try:
            screen_pos = self.world_to_screen_coord(world_coord)
            
            return (-margin <= screen_pos[0] <= self.screen_width + margin and
                    -margin <= screen_pos[1] <= self.screen_height + margin)
                    
        except Exception as e:
            logger.error("Error checking visibility: %s", e)
            return True  # Assume visible on error
            
    def get_visible_world_bounds(self) -> Tuple[WorldCoordinate, WorldCoordinate]:
        """Get world coordinate bounds of visible area."""
        try:
            # Top-left corner
            top_left = self.screen_to_world(0, 0)
            
            # Bottom-right corner
            bottom_right = self.screen_to_world(self.screen_width, self.screen_height)
            
            return (top_left, bottom_right)
            
        except Exception as e:
            logger.error("Error getting visible world bounds: %s", e)
            center = WorldCoordinate(0, 0, 0.0, 0.0)
            return (center, center)
            
    def _invalidate_cache(self):
        """Invalidate transformation cache."""
        with self._lock:
            self._cache_valid = False
            self._transform_cache.clear()
            
    def resize(self, new_width: int, new_height: int):
        """Resize viewport."""
        try:
            self.screen_width = new_width
            self.screen_height = new_height
            self._invalidate_cache()
            
            logger.debug("Viewport resized to %dx%d", new_width, new_height)
            
        except Exception as e:
            logger.error("Error resizing viewport: %s", e)
            
    def reset(self):
        """Reset viewport to origin."""
        try:
            self.center = WorldCoordinate(0, 0, 0.0, 0.0)
            self.zoom_level = 1.0
            self._invalidate_cache()
            
            logger.info("Viewport reset to origin")
            
        except Exception as e:
            logger.error("Error resetting viewport: %s", e)
            
    def get_stats(self) -> Dict[str, Any]:
        """Get viewport statistics."""
        try:
            center_world = self.center.to_world_float()
            bounds = self.get_visible_world_bounds()
            
            return {
                'center_world': center_world,
                'center_cell': (self.center.cell_x, self.center.cell_y),
                'zoom_level': self.zoom_level,
                'screen_size': (self.screen_width, self.screen_height),
                'visible_bounds': {
                    'top_left': bounds[0].to_world_float(),
                    'bottom_right': bounds[1].to_world_float()
                }
            }
        except Exception as e:
            logger.error("Error getting viewport stats: %s", e)
            return {}


class CoordinateManager:
    """
    Central manager for coordinate system operations.
    
    Provides high-level interface for coordinate transformations,
    bounds checking, and viewport management.
    """
    
    def __init__(self, screen_width: int, screen_height: int):
        self.viewport = Viewport(screen_width, screen_height)
        self._coordinate_cache = {}
        self._cache_size_limit = 1000
        self._lock = threading.Lock()
        
    def screen_to_world_coord(self, screen_x: int, screen_y: int) -> WorldCoordinate:
        """Convert screen position to world coordinate."""
        return self.viewport.screen_to_world(screen_x, screen_y)
        
    def world_coord_to_screen(self, world_coord: WorldCoordinate) -> Tuple[int, int]:
        """Convert world coordinate to screen position."""
        return self.viewport.world_to_screen_coord(world_coord)
        
    def world_float_to_screen(self, world_x: float, world_y: float) -> Tuple[int, int]:
        """Convert world float coordinates to screen position."""
        return self.viewport.world_to_screen(world_x, world_y)
        
    def pan_viewport(self, screen_dx: int, screen_dy: int):
        """Pan the viewport."""
        self.viewport.pan(screen_dx, screen_dy)
        self._clear_cache()
        
    def zoom_viewport(self, factor: float, screen_center: Tuple[int, int]):
        """Zoom the viewport."""
        self.viewport.zoom(factor, screen_center)
        self._clear_cache()
        
    def clamp_world_coordinate(self, world_coord: WorldCoordinate) -> WorldCoordinate:
        """Clamp world coordinate to system bounds."""
        try:
            # Coordinates are automatically clamped in WorldCoordinate constructor
            return WorldCoordinate(
                world_coord.cell_x, 
                world_coord.cell_y, 
                world_coord.local_x, 
                world_coord.local_y
            )
        except Exception as e:
            logger.error("Error clamping coordinate: %s", e)
            return WorldCoordinate(0, 0, 0.0, 0.0)
            
    def is_coordinate_valid(self, world_coord: WorldCoordinate) -> bool:
        """Check if coordinate is within system bounds."""
        try:
            return (abs(world_coord.cell_x) <= MAX_CELLS and
                    abs(world_coord.cell_y) <= MAX_CELLS and
                    0.0 <= world_coord.local_x < CELL_SIZE and
                    0.0 <= world_coord.local_y < CELL_SIZE)
        except Exception:
            return False
            
    def get_coordinate_precision(self, world_coord: WorldCoordinate) -> float:
        """Get coordinate precision at this position."""
        try:
            # Precision decreases with distance from origin
            distance_from_origin = world_coord.distance_to(WorldCoordinate(0, 0, 0.0, 0.0))
            
            # Base precision is 0.1 units, degrades with distance
            base_precision = 0.1
            distance_factor = min(distance_from_origin / 1000000.0, 10.0)  # Max 10x degradation
            
            return base_precision * (1.0 + distance_factor)
            
        except Exception as e:
            logger.error("Error calculating coordinate precision: %s", e)
            return 1.0  # Safe fallback
            
    def _clear_cache(self):
        """Clear coordinate transformation cache."""
        with self._lock:
            self._coordinate_cache.clear()
            
    def resize(self, new_width: int, new_height: int):
        """Resize the coordinate system."""
        self.viewport.resize(new_width, new_height)
        self._clear_cache()
        
    def reset(self):
        """Reset coordinate system to defaults."""
        self.viewport.reset()
        self._clear_cache()
        
    def get_system_info(self) -> Dict[str, Any]:
        """Get coordinate system information."""
        try:
            return {
                'cell_size': CELL_SIZE,
                'max_cells': MAX_CELLS,
                'max_world_coord': MAX_WORLD_COORD,
                'min_world_coord': MIN_WORLD_COORD,
                'viewport_stats': self.viewport.get_stats(),
                'cache_size': len(self._coordinate_cache)
            }
        except Exception as e:
            logger.error("Error getting system info: %s", e)
            return {}


# Utility functions for coordinate conversion
def create_world_coordinate(x: float, y: float) -> WorldCoordinate:
    """Create world coordinate from float values."""
    return WorldCoordinate.from_world(x, y)


def convert_points_to_world(points: List[Tuple[float, float]]) -> List[WorldCoordinate]:
    """Convert list of float points to world coordinates."""
    try:
        return [WorldCoordinate.from_world(x, y) for x, y in points]
    except Exception as e:
        logger.error("Error converting points to world coordinates: %s", e)
        return []


def convert_world_to_points(world_coords: List[WorldCoordinate]) -> List[Tuple[float, float]]:
    """Convert list of world coordinates to float points."""
    try:
        return [coord.to_world_float() for coord in world_coords]
    except Exception as e:
        logger.error("Error converting world coordinates to points: %s", e)
        return []


def interpolate_world_coordinates(start: WorldCoordinate, end: WorldCoordinate, steps: int) -> List[WorldCoordinate]:
    """Interpolate between two world coordinates."""
    try:
        if steps <= 1:
            return [start, end]
            
        start_world = start.to_world_float()
        end_world = end.to_world_float()
        
        result = []
        for i in range(steps + 1):
            t = i / steps
            
            interp_x = start_world[0] + t * (end_world[0] - start_world[0])
            interp_y = start_world[1] + t * (end_world[1] - start_world[1])
            
            result.append(WorldCoordinate.from_world(interp_x, interp_y))
            
        return result
        
    except Exception as e:
        logger.error("Error interpolating world coordinates: %s", e)
        return [start, end]