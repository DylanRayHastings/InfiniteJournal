import pygame

# --- Display Constants ---
WIDTH: int    = 800
HEIGHT: int   = 600
FPS: int      = 60

# --- Grid Constants ---
CELL_SIZE: int    = 20
MAJOR_INTERVAL: int = 5
LINE_SPACING: int = 30

# --- Color Constants ---
COLORS = {
    'bg_note':    (  0,   0,   0),
    'bg_graph':   ( 20,  20,  20),
    'note_line':  (120, 120, 120),
    'note_margin':(200, 200, 200),
    'grid_minor': ( 50,  50,  50),
    'grid_major': (100, 100, 100),
}

BRUSH_COLORS = {
    1: (255,255,255),
    2: (255,150,150),
    3: (150,255,150),
    4: (150,150,255),
    5: (255,255,150),
}
BRUSH_SIZES = [2, 4, 7, 9, 12]

FONT_PATH: str = 'Saira-Italic.ttf'
FONT_SIZE: int = 24

# --- Tool Modes ---
TOOL_BRUSH  = 'brush'
TOOL_LINE   = 'line'
TOOL_RECT   = 'rect'
TOOL_CIRCLE = 'circle'
TOOL_TRIANGLE  = 'triangle'
TOOL_PARABOLA  = 'parabola'

TOOLS       = [TOOL_BRUSH, TOOL_LINE, TOOL_RECT, TOOL_CIRCLE, TOOL_TRIANGLE, TOOL_PARABOLA]
DEFAULT_TOOL = TOOL_BRUSH