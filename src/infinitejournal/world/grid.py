# src/infinitejournal/world/grid.py
"""Shader-based infinite grid renderer."""

import numpy as np
from OpenGL.GL import *
import logging


class GridRenderer:
    """Renders an infinite grid using a single quad and shaders."""
    
    # Vertex shader for the grid
    VERTEX_SHADER = """
    #version 330 core
    
    layout(location = 0) in vec3 aPos;
    
    uniform mat4 viewProjection;
    
    out vec3 nearPoint;
    out vec3 farPoint;
    out mat4 fragView;
    out mat4 fragProj;
    
    vec3 UnprojectPoint(float x, float y, float z, mat4 view, mat4 projection) {
        mat4 viewInv = inverse(view);
        mat4 projInv = inverse(projection);
        vec4 unprojectedPoint = viewInv * projInv * vec4(x, y, z, 1.0);
        return unprojectedPoint.xyz / unprojectedPoint.w;
    }
    
    void main() {
        // Create a fullscreen quad
        vec3 gridPlane[4] = vec3[](
            vec3(-1, -1, 0),
            vec3( 1, -1, 0),
            vec3(-1,  1, 0),
            vec3( 1,  1, 0)
        );
        
        vec3 p = gridPlane[gl_VertexID].xyz;
        
        // Pass matrices to fragment shader
        fragView = viewProjection;
        fragProj = viewProjection;
        
        // Unproject points to world space
        nearPoint = UnprojectPoint(p.x, p.y, 0.0, fragView, fragProj).xyz;
        farPoint = UnprojectPoint(p.x, p.y, 1.0, fragView, fragProj).xyz;
        
        gl_Position = vec4(p, 1.0);
    }
    """
    
    # Fragment shader for the grid
    FRAGMENT_SHADER = """
    #version 330 core
    
    in vec3 nearPoint;
    in vec3 farPoint;
    in mat4 fragView;
    in mat4 fragProj;
    
    out vec4 FragColor;
    
    uniform float near;
    uniform float far;
    uniform vec3 gridColor;
    uniform vec3 axisColorX;
    uniform vec3 axisColorZ;
    uniform float gridSize;
    uniform float gridSubdivisions;
    uniform float fadeDistance;
    uniform float lineWidth;
    
    vec4 grid(vec3 fragPos3D, float scale) {
        vec2 coord = fragPos3D.xz * scale;
        vec2 derivative = fwidth(coord);
        vec2 grid = abs(fract(coord - 0.5) - 0.5) / derivative;
        float line = min(grid.x, grid.y);
        float minimumz = min(derivative.y, 1);
        float minimumx = min(derivative.x, 1);
        vec4 color = vec4(gridColor, 1.0 - min(line, 1.0));
        
        // Highlight axes
        if(fragPos3D.x > -lineWidth * minimumx && fragPos3D.x < lineWidth * minimumx)
            color = vec4(axisColorZ, 1.0);
        if(fragPos3D.z > -lineWidth * minimumz && fragPos3D.z < lineWidth * minimumz)
            color = vec4(axisColorX, 1.0);
            
        return color;
    }
    
    float computeDepth(vec3 pos) {
        vec4 clip_space_pos = fragProj * vec4(pos.xyz, 1.0);
        float ndc_depth = clip_space_pos.z / clip_space_pos.w;
        return (ndc_depth + 1.0) * 0.5;
    }
    
    float computeLinearDepth(vec3 pos) {
        vec4 clip_space_pos = fragProj * vec4(pos.xyz, 1.0);
        float clip_space_depth = clip_space_pos.z / clip_space_pos.w;
        float linearDepth = (2.0 * near * far) / (far + near - clip_space_depth * (far - near));
        return linearDepth / far;
    }
    
    void main() {
        // Ray-plane intersection
        float t = -nearPoint.y / (farPoint.y - nearPoint.y);
        
        // Only render if intersection is valid
        if (t < 0.0 || t > 1.0) {
            discard;
        }
        
        vec3 fragPos3D = nearPoint + t * (farPoint - nearPoint);
        
        // Compute depth for proper occlusion
        gl_FragDepth = computeDepth(fragPos3D);
        
        // Compute linear depth for fading
        float linearDepth = computeLinearDepth(fragPos3D);
        float fading = max(0, (fadeDistance - linearDepth) / fadeDistance);
        
        // Main grid
        vec4 mainGrid = grid(fragPos3D, 1.0 / gridSize);
        
        // Subdivisions (smaller grid)
        vec4 subGrid = grid(fragPos3D, gridSubdivisions / gridSize);
        subGrid.a *= 0.5; // Make subdivisions more subtle
        
        // Combine grids
        FragColor = mainGrid;
        FragColor.a = max(mainGrid.a, subGrid.a) * fading;
        
        // Discard nearly transparent fragments
        if (FragColor.a < 0.01)
            discard;
    }
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Grid settings
        self.grid_size = 1.0  # Size of main grid squares
        self.grid_subdivisions = 10.0  # Number of subdivisions
        self.grid_color = np.array([0.3, 0.3, 0.3], dtype=np.float32)
        self.axis_color_x = np.array([0.8, 0.2, 0.2], dtype=np.float32)  # Red for X
        self.axis_color_z = np.array([0.2, 0.2, 0.8], dtype=np.float32)  # Blue for Z
        self.fade_distance = 0.8  # Fade based on depth (0-1)
        self.line_width = 0.1
        
        # OpenGL objects
        self.vao = None
        self.shader_program = None
        self.uniform_locations = {}
        
        self._initialized = False
        
    def initialize(self):
        """Initialize OpenGL resources."""
        if self._initialized:
            return
            
        try:
            # Create and compile shaders
            self.shader_program = self._create_shader_program(
                self.VERTEX_SHADER,
                self.FRAGMENT_SHADER
            )
            
            # Get uniform locations
            self._get_uniform_locations()
            
            # Create VAO for rendering
            self.vao = glGenVertexArrays(1)
            
            self._initialized = True
            self.logger.info("Grid renderer initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize grid renderer: {e}")
            raise
            
    def render(self, camera, near=0.1, far=1000.0):
        """Render the infinite grid."""
        if not self._initialized:
            self.initialize()
            
        # Use shader program
        glUseProgram(self.shader_program)
        
        # Set uniforms
        view_projection = camera.get_view_projection_matrix()
        glUniformMatrix4fv(self.uniform_locations['viewProjection'], 1, GL_TRUE, view_projection)
        
        glUniform1f(self.uniform_locations['near'], near)
        glUniform1f(self.uniform_locations['far'], far)
        glUniform3fv(self.uniform_locations['gridColor'], 1, self.grid_color)
        glUniform3fv(self.uniform_locations['axisColorX'], 1, self.axis_color_x)
        glUniform3fv(self.uniform_locations['axisColorZ'], 1, self.axis_color_z)
        glUniform1f(self.uniform_locations['gridSize'], self.grid_size)
        glUniform1f(self.uniform_locations['gridSubdivisions'], self.grid_subdivisions)
        glUniform1f(self.uniform_locations['fadeDistance'], self.fade_distance)
        glUniform1f(self.uniform_locations['lineWidth'], self.line_width)
        
        # Enable blending for transparency
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        
        # Render the quad
        glBindVertexArray(self.vao)
        glDrawArrays(GL_TRIANGLE_STRIP, 0, 4)
        glBindVertexArray(0)
        
        # Disable blending
        glDisable(GL_BLEND)
        
        # Reset shader
        glUseProgram(0)
        
    def set_grid_size(self, size: float):
        """Set the size of grid squares."""
        self.grid_size = max(0.1, size)
        
    def set_grid_color(self, color: tuple):
        """Set the grid line color."""
        self.grid_color = np.array(color[:3], dtype=np.float32)
        
    def set_fade_distance(self, distance: float):
        """Set the fade distance (0-1)."""
        self.fade_distance = np.clip(distance, 0.0, 1.0)
        
    def cleanup(self):
        """Clean up OpenGL resources."""
        if self.vao:
            glDeleteVertexArrays(1, [self.vao])
        if self.shader_program:
            glDeleteProgram(self.shader_program)
        self._initialized = False
        
    def _create_shader_program(self, vertex_source: str, fragment_source: str) -> int:
        """Create and link a shader program."""
        # Create vertex shader
        vertex_shader = glCreateShader(GL_VERTEX_SHADER)
        glShaderSource(vertex_shader, vertex_source)
        glCompileShader(vertex_shader)
        
        # Check vertex shader compilation
        if not glGetShaderiv(vertex_shader, GL_COMPILE_STATUS):
            error = glGetShaderInfoLog(vertex_shader).decode()
            glDeleteShader(vertex_shader)
            raise RuntimeError(f"Vertex shader compilation failed: {error}")
            
        # Create fragment shader
        fragment_shader = glCreateShader(GL_FRAGMENT_SHADER)
        glShaderSource(fragment_shader, fragment_source)
        glCompileShader(fragment_shader)
        
        # Check fragment shader compilation
        if not glGetShaderiv(fragment_shader, GL_COMPILE_STATUS):
            error = glGetShaderInfoLog(fragment_shader).decode()
            glDeleteShader(vertex_shader)
            glDeleteShader(fragment_shader)
            raise RuntimeError(f"Fragment shader compilation failed: {error}")
            
        # Create and link program
        program = glCreateProgram()
        glAttachShader(program, vertex_shader)
        glAttachShader(program, fragment_shader)
        glLinkProgram(program)
        
        # Check linking
        if not glGetProgramiv(program, GL_LINK_STATUS):
            error = glGetProgramInfoLog(program).decode()
            glDeleteShader(vertex_shader)
            glDeleteShader(fragment_shader)
            glDeleteProgram(program)
            raise RuntimeError(f"Shader program linking failed: {error}")
            
        # Clean up shaders (they're linked to the program now)
        glDeleteShader(vertex_shader)
        glDeleteShader(fragment_shader)
        
        return program
        
    def _get_uniform_locations(self):
        """Get and cache uniform locations."""
        uniforms = [
            'viewProjection', 'near', 'far', 'gridColor',
            'axisColorX', 'axisColorZ', 'gridSize', 'gridSubdivisions',
            'fadeDistance', 'lineWidth'
        ]
        
        for uniform in uniforms:
            location = glGetUniformLocation(self.shader_program, uniform)
            if location == -1:
                self.logger.warning(f"Uniform '{uniform}' not found in shader")
            self.uniform_locations[uniform] = location