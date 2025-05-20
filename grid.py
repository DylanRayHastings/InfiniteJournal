import pygame
from config import CELL_SIZE, MAJOR_INTERVAL, LINE_SPACING, COLORS

class GridRenderer:
    """Draws notebook or graph grid on any surface dimension."""
    def __init__(self, surface: pygame.Surface):
        self.surface = surface

    def draw_notebook(self) -> None:
        width = self.surface.get_width()
        height = self.surface.get_height()
        # Horizontal ruled lines
        y = 0
        while y < height:
            pygame.draw.line(self.surface, COLORS['note_line'], (0, y), (width, y), 1)
            y += LINE_SPACING
        # Vertical margin line
        margin_x = width // 8
        pygame.draw.line(self.surface, COLORS['note_margin'], (margin_x, 0), (margin_x, height), 2)

    def draw_graph(self, camera_offset: pygame.Vector2) -> None:
        width = self.surface.get_width()
        height = self.surface.get_height()
        ox, oy = camera_offset.xy
        # Vertical grid lines
        start_x = int(ox // CELL_SIZE * CELL_SIZE)
        end_x = int((ox + width) // CELL_SIZE * CELL_SIZE + CELL_SIZE)
        for world_x in range(start_x, end_x, CELL_SIZE):
            x = int(world_x - ox)
            idx = world_x // CELL_SIZE
            color = COLORS['grid_major'] if idx % MAJOR_INTERVAL == 0 else COLORS['grid_minor']
            thickness = 2 if idx % MAJOR_INTERVAL == 0 else 1
            pygame.draw.line(self.surface, color, (x, 0), (x, height), thickness)
        # Horizontal grid lines
        start_y = int(oy // CELL_SIZE * CELL_SIZE)
        end_y = int((oy + height) // CELL_SIZE * CELL_SIZE + CELL_SIZE)
        for world_y in range(start_y, end_y, CELL_SIZE):
            y = int(world_y - oy)
            idx = world_y // CELL_SIZE
            color = COLORS['grid_major'] if idx % MAJOR_INTERVAL == 0 else COLORS['grid_minor']
            thickness = 2 if idx % MAJOR_INTERVAL == 0 else 1
            pygame.draw.line(self.surface, color, (0, y), (width, y), thickness)
