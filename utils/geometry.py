"""
Pan and zoom math for coordinates.
"""
from typing import Tuple

def pan(point: Tuple[int, int], offset: Tuple[int, int]) -> Tuple[int, int]:
    """
    Translate a point by the given offset.
    """
    return (point[0] + offset[0], point[1] + offset[1])

def zoom(point: Tuple[int, int], center: Tuple[int, int], factor: float) -> Tuple[int, int]:
    """
    Scale a point relative to a center by factor.
    """
    dx = point[0] - center[0]
    dy = point[1] - center[1]
    return (center[0] + int(dx * factor), center[1] + int(dy * factor))