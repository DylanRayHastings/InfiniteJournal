import math
from typing import List, Tuple

class NeonGrid:
    """
    Generates mathematical neon grid line coordinates for background rendering.

    Args:
        width (int): Width of the grid area.
        height (int): Height of the grid area.
        spacing (int): Grid spacing in pixels (default: 40).
    """

    def __init__(self, width: int, height: int, spacing: int = 40) -> None:
        self.width = width
        self.height = height
        self.spacing = spacing

    def grid_lines(self) -> List[Tuple[Tuple[int, int], Tuple[int, int], Tuple[int, int]]]:
        """
        Computes all grid line segments with neon color effects.

        Returns:
            List of tuples: [((x1, y1), (x2, y2), (r, g, b)), ...]
        """
        lines = []
        # Vertical lines
        for x in range(0, self.width, self.spacing):
            color = self._neon_color(x, axis='x')
            lines.append( ((x, 0), (x, self.height), color) )
        # Horizontal lines
        for y in range(0, self.height, self.spacing):
            color = self._neon_color(y, axis='y')
            lines.append( ((0, y), (self.width, y), color) )
        return lines

    def _neon_color(self, val: int, axis: str = 'x') -> Tuple[int, int, int]:
        """
        Generates a neon color tuple for a given grid line.

        Args:
            val (int): Position value (x or y).
            axis (str): 'x' for vertical, 'y' for horizontal lines.

        Returns:
            Tuple[int, int, int]: RGB color.
        """
        base_color = (0, 255, 255)  # Default cyan neon
        pulse = int(96 + 64 * math.sin(val / 80.0))
        if axis == 'x':
            return (pulse, 255, 255)
        else:
            return (0, min(pulse + 128, 255), 255)
