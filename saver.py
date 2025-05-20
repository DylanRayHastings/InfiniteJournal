import pygame
import os
import datetime
import logging
from config import (
    WIDTH, HEIGHT, COLORS,
    CELL_SIZE, MAJOR_INTERVAL, LINE_SPACING,
    TOOL_BRUSH, TOOL_LINE, TOOL_RECT,
    TOOL_CIRCLE, TOOL_TRIANGLE, TOOL_PARABOLA
)
from grid import GridRenderer

# Ensure logger is defined
logger = logging.getLogger('InfiniteJournal')

class SaveManager:
    """Handles saving snapshots of the entire infinite canvas."""
    def __init__(self, app):
        self.app = app

    def save_full_canvas(self):
        # 1) Compute content bounds across strokes, shapes, and texts
        xs, ys = [], []
        for pos, _, _ in self.app.strokes:
            xs.append(pos.x); ys.append(pos.y)
        for tool, start, end, _, _ in self.app.shapes:
            xs.extend([start.x, end.x]); ys.extend([start.y, end.y])
        for text, pos, _ in getattr(self.app, 'texts', []):
            xs.append(pos.x); ys.append(pos.y)

        if xs and ys:
            min_x, max_x = min(xs), max(xs)
            min_y, max_y = min(ys), max(ys)
        else:
            min_x, min_y = 0, 0
            max_x, max_y = WIDTH, HEIGHT

        # 2) Add padding
        pad = 20
        min_x -= pad; min_y -= pad
        max_x += pad; max_y += pad

        w_px = int(max_x - min_x)
        h_px = int(max_y - min_y)

        # 3) Create off-screen surface
        surface = pygame.Surface((w_px, h_px))
        surface.fill(COLORS[f'bg_{self.app.grid_mode}'])

        # 4) Draw grid on full canvas in graph mode
        if self.app.grid_mode == 'graph':
            gr = GridRenderer(surface)
            gr.draw_graph(pygame.Vector2(min_x, min_y))

        # 5) Draw strokes
        for pos, color, size in self.app.strokes:
            px = int(pos.x - min_x)
            py = int(pos.y - min_y)
            pygame.draw.circle(surface, color, (px, py), size)

        # 6) Draw shapes (reuse existing logic from renderer)
        for tool, start, end, color, size in self.app.shapes:
            s = pygame.Vector2(start.x - min_x, start.y - min_y)
            e = pygame.Vector2(end.x   - min_x, end.y   - min_y)
            # ... shape drawing logic omitted for brevity ...

        # 7) Draw texts
        for text, pos, color in getattr(self.app, 'texts', []):
            px = int(pos.x - min_x)
            py = int(pos.y - min_y)
            surface.blit(self.app.font.render(text, True, color), (px, py))

                        # 8) Ensure screenshots dir exists for default saving location
        screenshots_dir = os.path.join(os.getcwd(), 'Screenshots')
        os.makedirs(screenshots_dir, exist_ok=True)

        # Prepare default filename components
        date_str = datetime.datetime.now().strftime('%m_%d_%Y')
        mode_label = 'GRID' if self.app.grid_mode == 'graph' else 'NOTE'

        # 9) Prompt user with Save As dialog to choose filename and location
        screenshots_dir = os.path.join(os.getcwd(), 'Screenshots')
        os.makedirs(screenshots_dir, exist_ok=True)

        # 9) Prompt user with Save As dialog to choose filename and location
        try:
            import tkinter as tk
            from tkinter import filedialog
            root = tk.Tk()
            root.withdraw()
            # Suggest default filename and directory
            default_filename = f"{mode_label}_{date_str}.png"
            file_path = filedialog.asksaveasfilename(
                title="Save Screenshot As",
                initialdir=screenshots_dir,
                initialfile=default_filename,
                defaultextension=".png",
                filetypes=[("PNG Image", "*.png")]
            )
            root.destroy()
        except Exception as e:
            logger.error(f"Save dialog failed: {e}")
            file_path = None

        # 10) Save if a path was chosen
        if file_path:
            try:
                pygame.image.save(surface, file_path)
                logger.info(f"Saved full canvas to {file_path}")
            except Exception as e:
                logger.error(f"Failed to save screenshot: {e}")
