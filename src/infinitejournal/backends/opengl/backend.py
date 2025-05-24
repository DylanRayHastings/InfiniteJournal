"""OpenGL backend implementation."""

import logging
import pygame
from pygame.locals import *
from OpenGL.GL import *
from OpenGL.GLU import *

from infinitejournal.backends.base import Backend
from infinitejournal.config import Config


class OpenGLBackend(Backend):
    """OpenGL rendering backend using Pygame."""
    
    def __init__(self, config: Config):
        """Initialize OpenGL backend."""
        super().__init__(config)
        self.logger = logging.getLogger(__name__)
        self.screen = None
        self.clock = None
        self.running = False
        
    def initialize(self):
        """Initialize Pygame and OpenGL context."""
        self.logger.info("Initializing OpenGL backend...")
        
        # Initialize Pygame
        pygame.init()
        
        # Set OpenGL attributes
        pygame.display.gl_set_attribute(pygame.GL_CONTEXT_MAJOR_VERSION, self.config.gl_version[0])
        pygame.display.gl_set_attribute(pygame.GL_CONTEXT_MINOR_VERSION, self.config.gl_version[1])
        pygame.display.gl_set_attribute(pygame.GL_CONTEXT_PROFILE_MASK, pygame.GL_CONTEXT_PROFILE_CORE)
        pygame.display.gl_set_attribute(pygame.GL_DOUBLEBUFFER, 1)
        pygame.display.gl_set_attribute(pygame.GL_DEPTH_SIZE, 24)
        
        # Create window
        flags = pygame.OPENGL | pygame.DOUBLEBUF
        if self.config.fullscreen:
            flags |= pygame.FULLSCREEN
        
        self.screen = pygame.display.set_mode(
            (self.config.window_width, self.config.window_height),
            flags
        )
        
        pygame.display.set_caption(self.config.window_title)
        
        # Initialize OpenGL
        glEnable(GL_DEPTH_TEST)
        glDepthFunc(GL_LESS)
        
        # Set clear color
        glClearColor(*self.config.clear_color)
        
        # Setup viewport
        glViewport(0, 0, self.config.window_width, self.config.window_height)
        
        # Create clock for FPS limiting
        self.clock = pygame.time.Clock()
        
        self.logger.info(f"OpenGL Version: {glGetString(GL_VERSION).decode()}")
        self.logger.info(f"OpenGL Renderer: {glGetString(GL_RENDERER).decode()}")
        
    def clear(self):
        """Clear the screen."""
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        
    def present(self):
        """Present the rendered frame."""
        pygame.display.flip()
        
    def handle_events(self):
        """Handle window events."""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.running = False
                elif event.key == pygame.K_F11:
                    self.toggle_fullscreen()
    
    def toggle_fullscreen(self):
        """Toggle fullscreen mode."""
        self.config.fullscreen = not self.config.fullscreen
        flags = pygame.OPENGL | pygame.DOUBLEBUF
        if self.config.fullscreen:
            flags |= pygame.FULLSCREEN
        
        self.screen = pygame.display.set_mode(
            (self.config.window_width, self.config.window_height),
            flags
        )
        
        # Reset viewport
        glViewport(0, 0, self.config.window_width, self.config.window_height)
        
    def get_delta_time(self):
        """Get time since last frame in seconds."""
        return self.clock.tick(self.config.target_fps) / 1000.0
        
    def shutdown(self):
        """Shutdown the backend."""
        self.logger.info("Shutting down OpenGL backend...")
        pygame.quit()
        
    def is_running(self):
        """Check if the backend is still running."""
        return self.running
        
    def start(self):
        """Start the backend."""
        self.running = True
