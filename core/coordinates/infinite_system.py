# core/coordinates/infinite_system.py (OPTIMIZED)
"""
Hierarchical Coordinate System for InfiniteJournal

Handles large-scale coordinates using grid cells and local offsets.
Optimizations: __slots__, reduced validation, cached calculations, faster math.
"""

import logging
import math
from typing import Tuple, List, Optional, Dict, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# Constants - made immutable for performance
CELL_SIZE = 4096
MAX_CELLS = 16384
MAX_LOCAL_COORD = CELL_SIZE - 1
MIN_LOCAL_COORD = 0
MAX_WORLD_COORD = MAX_CELLS * CELL_SIZE
MIN_WORLD_COORD = -MAX_CELLS * CELL_SIZE

class CoordinateError(Exception):
    """Raised when coordinate operations fail."""
    __slots__ = ()

@dataclass(frozen=True, slots=True)  # slots for memory efficiency
class WorldCoordinate:
    """Hierarchical coordinate with cell and local offset."""
    cell_x: int = 0
    cell_y: int = 0
    local_x: float = 0.0
    local_y: float = 0.0
    
    def __post_init__(self):
        """Fast normalization and validation."""
        # Normalize local coordinates efficiently
        if self.local_x >= CELL_SIZE or self.local_x < 0:
            cell_offset = int(self.local_x // CELL_SIZE)
            object.__setattr__(self, 'cell_x', self.cell_x + cell_offset)
            object.__setattr__(self, 'local_x', self.local_x - cell_offset * CELL_SIZE)
            
        if self.local_y >= CELL_SIZE or self.local_y < 0:
            cell_offset = int(self.local_y // CELL_SIZE)
            object.__setattr__(self, 'cell_y', self.cell_y + cell_offset)
            object.__setattr__(self, 'local_y', self.local_y - cell_offset * CELL_SIZE)
        
        # Clamp to bounds - faster than try/except
        object.__setattr__(self, 'cell_x', max(-MAX_CELLS, min(MAX_CELLS, self.cell_x)))
        object.__setattr__(self, 'cell_y', max(-MAX_CELLS, min(MAX_CELLS, self.cell_y)))
        object.__setattr__(self, 'local_x', max(0.0, min(float(CELL_SIZE - 1), self.local_x)))
        object.__setattr__(self, 'local_y', max(0.0, min(float(CELL_SIZE - 1), self.local_y)))
        
    def to_world_float(self) -> Tuple[float, float]:
        """Convert to world coordinates - optimized."""
        return (
            float(self.cell_x * CELL_SIZE) + self.local_x,
            float(self.cell_y * CELL_SIZE) + self.local_y
        )
            
    def to_world_int(self) -> Tuple[int, int]:
        """Convert to world coordinates as integers."""
        world_x, world_y = self.to_world_float()
        return (int(world_x), int(world_y))
        
    @classmethod
    def from_world(cls, world_x: float, world_y: float) -> 'WorldCoordinate':
        """Create WorldCoordinate from world position - optimized."""
        # Fast division and modulo
        cell_x = int(world_x // CELL_SIZE) if world_x >= 0 else int((world_x - CELL_SIZE + 1) // CELL_SIZE)
        cell_y = int(world_y // CELL_SIZE) if world_y >= 0 else int((world_y - CELL_SIZE + 1) // CELL_SIZE)
        
        local_x = world_x - cell_x * CELL_SIZE
        local_y = world_y - cell_y * CELL_SIZE
        
        return cls(cell_x, cell_y, local_x, local_y)
            
    def distance_to(self, other: 'WorldCoordinate') -> float:
        """Calculate distance - optimized for speed."""
        self_world = self.to_world_float()
        other_world = other.to_world_float()
        
        dx = self_world[0] - other_world[0]
        dy = self_world[1] - other_world[1]
        
        return math.sqrt(dx * dx + dy * dy)
            
    def add_offset(self, dx: float, dy: float) -> 'WorldCoordinate':
        """Add offset and return new coordinate."""
        return WorldCoordinate(self.cell_x, self.cell_y, self.local_x + dx, self.local_y + dy)
            
    def is_in_same_cell(self) -> bool:
        """Check if two coordinates are in the same cell."""
        return self.cell_x == other.cell_x and self.cell_y == other.cell_y
        
    def __str__(self) -> str:
        return f"Cell({self.cell_x}, {self.cell_y}) + Local({self.local_x:.2f}, {self.local_y:.2f})"


class Viewport:
    """Viewport for converting between world and screen coordinates - optimized."""
    __slots__ = ('screen_width', 'screen_height', 'center', 'zoom_level', 
                 'min_zoom', 'max_zoom', '_transform_cache', '_cache_valid')
    
    def __init__(self, screen_width: int, screen_height: int):
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.center = WorldCoordinate(0, 0, 0.0, 0.0)
        self.zoom_level = 1.0
        self.min_zoom = 0.01
        self.max_zoom = 100.0
        self._transform_cache = {}
        self._cache_valid = False
        
    def pan(self, screen_dx: int, screen_dy: int) -> None:
        """Pan viewport - optimized."""
        world_dx = screen_dx / self.zoom_level
        world_dy = screen_dy / self.zoom_level
        self.center = self.center.add_offset(-world_dx, -world_dy)
        self._cache_valid = False
            
    def zoom(self, factor: float, screen_center: Tuple[int, int]) -> None:
        """Zoom viewport - optimized."""
        new_zoom = max(self.min_zoom, min(self.max_zoom, self.zoom_level * factor))
        
        if new_zoom == self.zoom_level:
            return
                
        world_center = self.screen_to_world(screen_center[0], screen_center[1])
        self.zoom_level = new_zoom
        new_screen_center = self.world_to_screen_coord(world_center)
        
        screen_offset_x = new_screen_center[0] - screen_center[0]
        screen_offset_y = new_screen_center[1] - screen_center[1]
        
        self.pan(screen_offset_x, screen_offset_y)
            
    def screen_to_world(self, screen_x: int, screen_y: int) -> WorldCoordinate:
        """Convert screen coordinates to world coordinates - optimized."""
        center_x = self.screen_width >> 1  # Fast division by 2
        center_y = self.screen_height >> 1
        
        offset_x = (screen_x - center_x) / self.zoom_level
        offset_y = (screen_y - center_y) / self.zoom_level
        
        return self.center.add_offset(offset_x, offset_y)
            
    def world_to_screen(self, world_x: float, world_y: float) -> Tuple[int, int]:
        """Convert world coordinates to screen coordinates - optimized."""
        world_coord = WorldCoordinate.from_world(world_x, world_y)
        return self.world_to_screen_coord(world_coord)
            
    def world_to_screen_coord(self, world_coord: WorldCoordinate) -> Tuple[int, int]:
        """Convert WorldCoordinate to screen coordinates - optimized."""
        center_world = self.center.to_world_float()
        coord_world = world_coord.to_world_float()
        
        world_offset_x = coord_world[0] - center_world[0]
        world_offset_y = coord_world[1] - center_world[1]
        
        screen_offset_x = world_offset_x * self.zoom_level
        screen_offset_y = world_offset_y * self.zoom_level
        
        screen_center_x = self.screen_width >> 1
        screen_center_y = self.screen_height >> 1
        
        return (int(screen_center_x + screen_offset_x), int(screen_center_y + screen_offset_y))
            
    def is_visible(self, world_coord: WorldCoordinate, margin: int = 100) -> bool:
        """Check if world coordinate is visible - optimized."""
        screen_pos = self.world_to_screen_coord(world_coord)
        return (-margin <= screen_pos[0] <= self.screen_width + margin and
                -margin <= screen_pos[1] <= self.screen_height + margin)
            
    def get_visible_world_bounds(self) -> Tuple[WorldCoordinate, WorldCoordinate]:
        """Get world coordinate bounds of visible area."""
        top_left = self.screen_to_world(0, 0)
        bottom_right = self.screen_to_world(self.screen_width, self.screen_height)
        return (top_left, bottom_right)
            
    def resize(self, new_width: int, new_height: int):
        """Resize viewport."""
        self.screen_width = new_width
        self.screen_height = new_height
        self._cache_valid = False
            
    def reset(self):
        """Reset viewport to origin."""
        self.center = WorldCoordinate(0, 0, 0.0, 0.0)
        self.zoom_level = 1.0
        self._cache_valid = False


class CoordinateManager:
    """Central manager for coordinate system operations - optimized."""
    __slots__ = ('viewport', '_coordinate_cache', '_cache_size_limit')
    
    def __init__(self, screen_width: int, screen_height: int):
        self.viewport = Viewport(screen_width, screen_height)
        self._coordinate_cache = {}
        self._cache_size_limit = 1000
        
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
        self._coordinate_cache.clear()
        
    def zoom_viewport(self, factor: float, screen_center: Tuple[int, int]):
        """Zoom the viewport."""
        self.viewport.zoom(factor, screen_center)
        self._coordinate_cache.clear()
        
    def clamp_world_coordinate(self, world_coord: WorldCoordinate) -> WorldCoordinate:
        """Clamp world coordinate to system bounds."""
        return WorldCoordinate(world_coord.cell_x, world_coord.cell_y, 
                             world_coord.local_x, world_coord.local_y)
            
    def is_coordinate_valid(self, world_coord: WorldCoordinate) -> bool:
        """Check if coordinate is within system bounds - optimized."""
        return (abs(world_coord.cell_x) <= MAX_CELLS and
                abs(world_coord.cell_y) <= MAX_CELLS and
                0.0 <= world_coord.local_x < CELL_SIZE and
                0.0 <= world_coord.local_y < CELL_SIZE)
            
    def get_coordinate_precision(self, world_coord: WorldCoordinate) -> float:
        """Get coordinate precision at this position."""
        distance_from_origin = world_coord.distance_to(WorldCoordinate(0, 0, 0.0, 0.0))
        base_precision = 0.1
        distance_factor = min(distance_from_origin / 1000000.0, 10.0)
        return base_precision * (1.0 + distance_factor)
            
    def resize(self, new_width: int, new_height: int):
        """Resize the coordinate system."""
        self.viewport.resize(new_width, new_height)
        self._coordinate_cache.clear()
        
    def reset(self):
        """Reset coordinate system to defaults."""
        self.viewport.reset()
        self._coordinate_cache.clear()


# Optimized utility functions - reduced function call overhead
def create_world_coordinate(x: float, y: float) -> WorldCoordinate:
    """Create world coordinate from float values."""
    return WorldCoordinate.from_world(x, y)

def convert_points_to_world(points: List[Tuple[float, float]]) -> List[WorldCoordinate]:
    """Convert list of float points to world coordinates - optimized."""
    return [WorldCoordinate.from_world(x, y) for x, y in points]

def convert_world_to_points(world_coords: List[WorldCoordinate]) -> List[Tuple[float, float]]:
    """Convert list of world coordinates to float points - optimized."""
    return [coord.to_world_float() for coord in world_coords]

def interpolate_world_coordinates(start: WorldCoordinate, end: WorldCoordinate, steps: int) -> List[WorldCoordinate]:
    """Interpolate between two world coordinates - optimized."""
    if steps <= 1:
        return [start, end]
        
    start_world = start.to_world_float()
    end_world = end.to_world_float()
    
    dx = end_world[0] - start_world[0]
    dy = end_world[1] - start_world[1]
    
    result = []
    for i in range(steps + 1):
        t = i / steps
        x = start_world[0] + t * dx
        y = start_world[1] + t * dy
        result.append(WorldCoordinate.from_world(x, y))
        
    return result