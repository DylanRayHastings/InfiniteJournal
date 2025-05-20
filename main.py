import pygame
import sys
from config import *
from input_handler import InputHandler
from config import TOOLS
from renderer import CanvasRenderer
from saver import SaveManager

class InfiniteJournal:
    """Entry point tying everything together."""
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.RESIZABLE)
        pygame.display.set_caption('InfiniteJournal')
        self.clock = pygame.time.Clock()

        # --- drawing state ---
        self.strokes       = []  # list of (world_pos, color, size)
        self.shapes        = []  # list of (tool, start, end, color, size)
        self.preview_shape = None
        self.current_tool  = DEFAULT_TOOL

        # --- brush settings ---
        self.brush_color = BRUSH_COLORS[1]
        self.brush_size  = BRUSH_SIZES[0]

        # --- camera, grid, text state ---
        self.grid_mode      = 'note'
        self.tool_mode      = 'draw'
        self.text_buffer    = ''
        self.text_world_pos = pygame.Vector2(0, 0)
        self.camera_offset  = pygame.Vector2(0, 0)

        # --- font setup ---
        try:
            self.font = pygame.font.Font(FONT_PATH, FONT_SIZE)
        except FileNotFoundError:
            print(f"Warning: '{FONT_PATH}' not found, using default font.")
            self.font = pygame.font.SysFont(None, FONT_SIZE)

        # --- panning state ---
        self.panning     = False
        self.pan_start   = pygame.Vector2(0, 0)
        self.orig_offset = pygame.Vector2(0, 0)

        # --- modules ---
        self.input_handler = InputHandler(self)
        self.renderer      = CanvasRenderer(self)
        self.save_manager  = SaveManager(self)

    def run(self):
        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                elif event.type == pygame.VIDEORESIZE:
                    self.screen = pygame.display.set_mode((event.w, event.h), pygame.RESIZABLE)
                    self.renderer.grid.surface = self.screen
                elif event.type == pygame.KEYDOWN:
                    # Handle key including backslash tool cycling
                    if event.key == pygame.K_BACKSLASH:
                        idx = TOOLS.index(self.current_tool)
                        self.current_tool = TOOLS[(idx + 1) % len(TOOLS)]
                    else:
                        self.handle_key(event)
                elif event.type == pygame.MOUSEWHEEL:
                    # Scroll wheel adjusts brush size
                    try:
                        idx = BRUSH_SIZES.index(self.brush_size)
                        new_idx = max(0, min(len(BRUSH_SIZES)-1, idx + event.y))
                        self.brush_size = BRUSH_SIZES[new_idx]
                    except ValueError:
                        # current size not in list, ignore
                        pass
                elif event.type in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP, pygame.MOUSEMOTION):
                    # dispatch mouse events directly
                    if event.type == pygame.MOUSEBUTTONDOWN:
                        self.handle_mouse_down(event)
                    elif event.type == pygame.MOUSEBUTTONUP:
                        self.handle_mouse_up(event)
                    elif event.type == pygame.MOUSEMOTION:
                        self.handle_mouse_move(event)

            self.renderer.render_frame()
            pygame.display.flip()
            self.clock.tick(FPS)

    def handle_key(self, event):
        mods, key, char = pygame.key.get_mods(), event.key, event.unicode
        # Toggle grid
        if key == pygame.K_TAB:
            self.grid_mode = 'graph' if self.grid_mode == 'note' else 'note'
            return
        # Toggle draw/text
        if key == pygame.K_t:
            if self.tool_mode == 'draw':
                self.tool_mode = 'text'
                self.text_buffer = ''
            else:
                self.tool_mode = 'draw'
            return
        # Save full canvas
        if key == pygame.K_s and mods & pygame.KMOD_CTRL and mods & pygame.KMOD_SHIFT:
            self.save_manager.save_full_canvas()
            return
        # Clear all
        if key == pygame.K_l and mods & pygame.KMOD_CTRL:
            self.strokes.clear()
            self.shapes.clear()
            return
        # Brush color change
        if self.tool_mode == 'draw' and char.isdigit() and int(char) in BRUSH_COLORS:
            self.brush_color = BRUSH_COLORS[int(char)]
            return
        # Text input
        if self.tool_mode == 'text':
            if key == pygame.K_RETURN:
                if mods & pygame.KMOD_SHIFT:
                    self.texts.append((self.text_buffer, self.text_world_pos.copy(), self.brush_color))
                    self.text_buffer = ''
                else:
                    self.text_buffer += '\n'
            elif key == pygame.K_BACKSPACE:
                self.text_buffer = self.text_buffer[:-1]
            else:
                self.text_buffer += char
            return

    def handle_mouse_down(self, event):
        """Begin drawing or start panning based on mouse button."""
        if event.button == 1:
            world_pos = pygame.Vector2(event.pos) + self.camera_offset
            if self.current_tool == TOOL_BRUSH:
                self.strokes.append((world_pos, self.brush_color, self.brush_size))
            else:
                self.preview_shape = [
                    self.current_tool,
                    world_pos.copy(),
                    world_pos.copy(),
                    self.brush_color,
                    self.brush_size
                ]
        elif event.button == 3:
            self.panning     = True
            self.pan_start   = pygame.Vector2(event.pos)
            self.orig_offset = self.camera_offset.copy()

    def handle_mouse_move(self, event):
        """Pan camera or draw strokes/shapes at world position under cursor."""
        # Panning priority
        if event.buttons[2] and self.panning:
            current = pygame.Vector2(event.pos)
            delta   = current - self.pan_start
            self.camera_offset = self.orig_offset - delta
            return
        # Drawing
        if event.buttons[0]:
            world_pos = pygame.Vector2(event.pos) + self.camera_offset
            if self.current_tool == TOOL_BRUSH:
                self.strokes.append((world_pos, self.brush_color, self.brush_size))
            elif self.preview_shape:
                self.preview_shape[2] = world_pos

    def handle_mouse_up(self, event):
        """Stop drawing or panning on mouse release."""
        if event.button == 1 and self.preview_shape:
            self.shapes.append(tuple(self.preview_shape))
            self.preview_shape = None
        elif event.button == 3 and self.panning:
            self.panning = False

if __name__ == '__main__':
    InfiniteJournal().run()
