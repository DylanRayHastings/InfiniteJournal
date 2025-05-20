from ui.grid import NeonGrid

class Notebook:
    """
    Notebook abstraction that manages the grid and additional drawing layers.

    Args:
        width (int): The width of the notebook/canvas area.
        height (int): The height of the notebook/canvas area.
    """

    def __init__(self, width: int, height: int) -> None:
        self.width = width
        self.height = height
        self.grid = NeonGrid(width, height)
        # TODO: add support for pages, strokes, selections, etc.

    def render(self, renderer) -> None:
        """
        Renders the neon grid and any notebook overlays.
        
        Args:
            renderer: The renderer object with a `draw_line` method that accepts
                      (start, end, width, color).
        """
        # Draw the neon grid background
        for start, end, color in self.grid.grid_lines():
            renderer.draw_line(start, end, 1, color)

        # TODO: strokes, selections, etc
