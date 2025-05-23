# InfiniteJournal

An infinite digital journal with drawing capabilities and optimized performance.

## Features

- **Persistent Drawing**: All strokes remain visible until explicitly cleared
- **Smooth Brush Strokes**: Optimized rendering eliminates gaps and lag
- **Multiple Tools**: Brush, eraser, line, triangle, parabola, and more
- **Performance Optimized**: Async persistence and optimized rendering
- **Configurable**: Environment variable configuration for all settings

## Controls

- **Mouse**: Left click and drag to draw
- **Number Keys (1-5)**: Change brush color to neon colors
- **+/-**: Increase/decrease brush size
- **Space**: Cycle through tools
- **C**: Clear canvas
- **Tool Keys**: Press tool name to switch (brush, eraser, line, etc.)

## Configuration

Set these environment variables to customize behavior:

### Performance Settings
- `IJ_FPS=60`: Target frame rate
- `IJ_MAX_FPS=120`: Maximum frame rate
- `IJ_STROKE_SMOOTHING=true`: Enable stroke smoothing
- `IJ_ASYNC_SAVE=true`: Enable asynchronous saving

### Drawing Settings
- `IJ_BRUSH_MIN=1`: Minimum brush size
- `IJ_BRUSH_MAX=100`: Maximum brush size
- `IJ_POINT_THRESHOLD=2`: Point distance threshold for smoothing

### Window Settings
- `IJ_WIDTH=1280`: Window width
- `IJ_HEIGHT=720`: Window height
- `IJ_TITLE="InfiniteJournal"`: Window title

## Running

```bash
python main.py