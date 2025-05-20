"""
Utility function to draw a grid background for the canvas.
"""

def draw_grid(engine, spacing=25, color=(40, 40, 40)):
    """
    Draws a mathematical grid as the background.

    Args:
        engine: The Engine instance used to draw.
        spacing (int): Distance between grid lines in pixels.
        color (tuple): RGB color of grid lines.
    """
    width, height = engine.screen.get_size()
    for x in range(0, width, spacing):
        engine.draw_line((x, 0), (x, height), 1, color)
    for y in range(0, height, spacing):
        engine.draw_line((0, y), (width, y), 1, color)
