# src/infinitejournal/world/player.py
"""Player controller for movement and interaction."""

import pygame
import numpy as np
from typing import Optional
from src.infinitejournal.world.camera import FPSCamera


class PlayerController:
    """Handles player input and movement."""
    
    def __init__(self, camera: Optional[FPSCamera] = None):
        """Initialize player controller."""
        self.camera = camera if camera is not None else FPSCamera()
        
        # Input state
        self.keys_pressed = {}
        self.mouse_captured = False
        self.mouse_delta = np.zeros(2)
        
        # Movement settings
        self.base_move_speed = 5.0
        self.sprint_multiplier = 2.0
        self.crouch_multiplier = 0.5
        self.jump_velocity = 8.0
        
        # Player state
        self.is_grounded = True
        self.is_sprinting = False
        self.is_crouching = False
        self.vertical_velocity = 0.0
        
        # Physics
        self.gravity = -20.0
        self.ground_height = 0.0
        
        # Mouse smoothing
        self.mouse_smoothing = 0.3
        self.smoothed_mouse_delta = np.zeros(2)
        
    def update(self, delta_time: float):
        """Update player state."""
        # Apply gravity if not grounded
        if not self.is_grounded:
            self.vertical_velocity += self.gravity * delta_time
            self.camera.position[1] += self.vertical_velocity * delta_time
            
            # Check if landed
            if self.camera.position[1] <= self.ground_height + 1.7:  # Eye height
                self.camera.position[1] = self.ground_height + 1.7
                self.vertical_velocity = 0.0
                self.is_grounded = True
                
        # Handle keyboard movement
        self._handle_movement(delta_time)
        
        # Handle mouse look with smoothing
        if self.mouse_captured and np.any(self.mouse_delta != 0):
            # Apply mouse smoothing
            self.smoothed_mouse_delta = (
                self.smoothed_mouse_delta * (1 - self.mouse_smoothing) +
                self.mouse_delta * self.mouse_smoothing
            )
            
            self.camera.handle_mouse_movement(
                self.smoothed_mouse_delta[0],
                self.smoothed_mouse_delta[1]
            )
            
            # Reset mouse delta
            self.mouse_delta = np.zeros(2)
            
        # Update camera
        self.camera.update(delta_time)
        
    def handle_event(self, event):
        """Handle pygame events."""
        if event.type == pygame.KEYDOWN:
            self._handle_key_down(event.key)
        elif event.type == pygame.KEYUP:
            self._handle_key_up(event.key)
        elif event.type == pygame.MOUSEBUTTONDOWN:
            self._handle_mouse_button_down(event.button)
        elif event.type == pygame.MOUSEBUTTONUP:
            self._handle_mouse_button_up(event.button)
        elif event.type == pygame.MOUSEMOTION:
            if self.mouse_captured:
                self.mouse_delta[0] += event.rel[0]
                self.mouse_delta[1] += event.rel[1]
                
    def _handle_key_down(self, key):
        """Handle key press."""
        if key == pygame.K_w:
            self.keys_pressed['w'] = True
        elif key == pygame.K_s:
            self.keys_pressed['s'] = True
        elif key == pygame.K_a:
            self.keys_pressed['a'] = True
        elif key == pygame.K_d:
            self.keys_pressed['d'] = True
        elif key == pygame.K_SPACE:
            self.keys_pressed['space'] = True
            if self.is_grounded:
                self._jump()
        elif key == pygame.K_LSHIFT:
            self.keys_pressed['shift'] = True
            self.is_sprinting = True
        elif key == pygame.K_LCTRL:
            self.keys_pressed['ctrl'] = True
            self.is_crouching = True
        elif key == pygame.K_TAB:
            self.toggle_mouse_capture()
            
    def _handle_key_up(self, key):
        """Handle key release."""
        if key == pygame.K_w:
            self.keys_pressed['w'] = False
        elif key == pygame.K_s:
            self.keys_pressed['s'] = False
        elif key == pygame.K_a:
            self.keys_pressed['a'] = False
        elif key == pygame.K_d:
            self.keys_pressed['d'] = False
        elif key == pygame.K_SPACE:
            self.keys_pressed['space'] = False
        elif key == pygame.K_LSHIFT:
            self.keys_pressed['shift'] = False
            self.is_sprinting = False
        elif key == pygame.K_LCTRL:
            self.keys_pressed['ctrl'] = False
            self.is_crouching = False
            
    def _handle_mouse_button_down(self, button):
        """Handle mouse button press."""
        if button == 1:  # Left click
            if not self.mouse_captured:
                self.toggle_mouse_capture()
                
    def _handle_mouse_button_up(self, button):
        """Handle mouse button release."""
        pass
        
    def _handle_movement(self, delta_time: float):
        """Process movement input."""
        # Pass key state to camera
        self.camera.handle_keyboard(self.keys_pressed, delta_time)
        
        # Adjust camera speed based on player state
        if self.is_sprinting and not self.is_crouching:
            self.camera.movement_speed = self.base_move_speed * self.sprint_multiplier
        elif self.is_crouching:
            self.camera.movement_speed = self.base_move_speed * self.crouch_multiplier
        else:
            self.camera.movement_speed = self.base_move_speed
            
    def _jump(self):
        """Make the player jump."""
        if self.is_grounded:
            self.vertical_velocity = self.jump_velocity
            self.is_grounded = False
            
    def toggle_mouse_capture(self):
        """Toggle mouse capture for looking around."""
        self.mouse_captured = not self.mouse_captured
        pygame.mouse.set_visible(not self.mouse_captured)
        pygame.mouse.set_grab(self.mouse_captured)
        
        if self.mouse_captured:
            # Center mouse
            pygame.mouse.set_pos(
                pygame.display.get_surface().get_width() // 2,
                pygame.display.get_surface().get_height() // 2
            )
            
    def get_position(self) -> np.ndarray:
        """Get player position."""
        return self.camera.position.copy()
        
    def set_position(self, position: np.ndarray):
        """Set player position."""
        self.camera.position = position.copy()
        
    def get_view_matrix(self) -> np.ndarray:
        """Get view matrix from camera."""
        return self.camera.get_view_matrix()
        
    def get_projection_matrix(self) -> np.ndarray:
        """Get projection matrix from camera."""
        return self.camera.get_projection_matrix()
        
    def get_view_projection_matrix(self) -> np.ndarray:
        """Get combined view-projection matrix."""
        return self.camera.get_view_projection_matrix()
        
    def set_aspect_ratio(self, aspect_ratio: float):
        """Update camera aspect ratio."""
        self.camera.set_aspect_ratio(aspect_ratio)
        
    def get_forward_vector(self) -> np.ndarray:
        """Get the forward direction vector."""
        return self.camera.front.copy()
        
    def get_right_vector(self) -> np.ndarray:
        """Get the right direction vector."""
        return self.camera.right.copy()
        
    def get_up_vector(self) -> np.ndarray:
        """Get the up direction vector."""
        return self.camera.up.copy()