# src/infinitejournal/world/camera.py
"""Camera system for 3D navigation."""

import numpy as np
from abc import ABC, abstractmethod
from typing import Tuple
import math


class Camera(ABC):
    """Abstract base camera class."""
    
    def __init__(self, position: np.ndarray = None, aspect_ratio: float = 16/9):
        self.position = position if position is not None else np.array([0.0, 1.0, 3.0], dtype=np.float32)
        self.aspect_ratio = aspect_ratio
        self._view_matrix = np.eye(4, dtype=np.float32)
        self._projection_matrix = np.eye(4, dtype=np.float32)
        self._view_projection_matrix = np.eye(4, dtype=np.float32)
        self._needs_update = True
        
    @abstractmethod
    def update(self, delta_time: float):
        """Update camera state."""
        pass
        
    @abstractmethod
    def handle_mouse_movement(self, dx: float, dy: float):
        """Handle mouse movement for camera rotation."""
        pass
        
    @abstractmethod
    def handle_keyboard(self, keys: dict, delta_time: float):
        """Handle keyboard input for camera movement."""
        pass
        
    def get_view_matrix(self) -> np.ndarray:
        """Get the view matrix."""
        if self._needs_update:
            self._update_matrices()
        return self._view_matrix
        
    def get_projection_matrix(self) -> np.ndarray:
        """Get the projection matrix."""
        if self._needs_update:
            self._update_matrices()
        return self._projection_matrix
        
    def get_view_projection_matrix(self) -> np.ndarray:
        """Get the combined view-projection matrix."""
        if self._needs_update:
            self._update_matrices()
        return self._view_projection_matrix
        
    @abstractmethod
    def _update_matrices(self):
        """Update internal matrices."""
        pass
        
    def set_aspect_ratio(self, aspect_ratio: float):
        """Update the aspect ratio."""
        self.aspect_ratio = aspect_ratio
        self._needs_update = True


class FPSCamera(Camera):
    """First-person shooter style camera."""
    
    def __init__(self, position: np.ndarray = None, aspect_ratio: float = 16/9,
                 fov: float = 45.0, near: float = 0.1, far: float = 1000.0):
        super().__init__(position, aspect_ratio)
        self.fov = fov
        self.near = near
        self.far = far
        
        # Euler angles
        self.yaw = -90.0  # Looking along -Z
        self.pitch = 0.0
        
        # Movement settings
        self.movement_speed = 5.0
        self.sprint_multiplier = 2.0
        self.mouse_sensitivity = 0.1
        
        # Camera vectors
        self.front = np.array([0.0, 0.0, -1.0], dtype=np.float32)
        self.up = np.array([0.0, 1.0, 0.0], dtype=np.float32)
        self.right = np.array([1.0, 0.0, 0.0], dtype=np.float32)
        
        # Movement state
        self.velocity = np.zeros(3, dtype=np.float32)
        self.acceleration = 20.0
        self.friction = 10.0
        
        self._update_camera_vectors()
        
    def update(self, delta_time: float):
        """Update camera state with smooth movement."""
        # Apply friction
        if np.linalg.norm(self.velocity) > 0.01:
            friction_force = -self.velocity * self.friction * delta_time
            self.velocity += friction_force
            
            # Stop if velocity is very small
            if np.linalg.norm(self.velocity) < 0.1:
                self.velocity = np.zeros(3, dtype=np.float32)
        
        # Update position
        if np.linalg.norm(self.velocity) > 0:
            self.position += self.velocity * delta_time
            self._needs_update = True
            
    def handle_mouse_movement(self, dx: float, dy: float):
        """Handle mouse movement for looking around."""
        self.yaw += dx * self.mouse_sensitivity
        self.pitch -= dy * self.mouse_sensitivity
        
        # Clamp pitch to prevent flipping
        self.pitch = np.clip(self.pitch, -89.0, 89.0)
        
        self._update_camera_vectors()
        self._needs_update = True
        
    def handle_keyboard(self, keys: dict, delta_time: float):
        """Handle WASD movement with acceleration."""
        # Calculate desired movement direction
        movement = np.zeros(3, dtype=np.float32)
        
        speed = self.movement_speed
        if keys.get('shift', False):
            speed *= self.sprint_multiplier
            
        if keys.get('w', False):
            movement += self.front
        if keys.get('s', False):
            movement -= self.front
        if keys.get('a', False):
            movement -= self.right
        if keys.get('d', False):
            movement += self.right
        if keys.get('space', False):
            movement += self.up
        if keys.get('ctrl', False):
            movement -= self.up
            
        # Normalize movement vector
        if np.linalg.norm(movement) > 0:
            movement = movement / np.linalg.norm(movement)
            
            # Apply acceleration
            target_velocity = movement * speed
            velocity_diff = target_velocity - self.velocity
            
            # Smooth acceleration
            if np.linalg.norm(velocity_diff) > 0:
                accel = velocity_diff / np.linalg.norm(velocity_diff) * self.acceleration
                self.velocity += accel * delta_time
                
                # Clamp to max speed
                if np.linalg.norm(self.velocity) > speed:
                    self.velocity = self.velocity / np.linalg.norm(self.velocity) * speed
                    
    def _update_camera_vectors(self):
        """Update camera orientation vectors from euler angles."""
        # Calculate front vector
        front = np.zeros(3, dtype=np.float32)
        front[0] = np.cos(np.radians(self.yaw)) * np.cos(np.radians(self.pitch))
        front[1] = np.sin(np.radians(self.pitch))
        front[2] = np.sin(np.radians(self.yaw)) * np.cos(np.radians(self.pitch))
        
        self.front = front / np.linalg.norm(front)
        self.right = np.cross(self.front, self.up)
        self.right = self.right / np.linalg.norm(self.right)
        
        # Recalculate up vector to ensure orthogonality
        self.up = np.cross(self.right, self.front)
        self.up = self.up / np.linalg.norm(self.up)
        
    def _update_matrices(self):
        """Update view and projection matrices."""
        # View matrix using lookAt
        self._view_matrix = self._look_at(
            self.position,
            self.position + self.front,
            self.up
        )
        
        # Projection matrix
        self._projection_matrix = self._perspective(
            np.radians(self.fov),
            self.aspect_ratio,
            self.near,
            self.far
        )
        
        # Combined matrix
        self._view_projection_matrix = self._projection_matrix @ self._view_matrix
        self._needs_update = False
        
    def _look_at(self, eye: np.ndarray, center: np.ndarray, up: np.ndarray) -> np.ndarray:
        """Create a look-at view matrix."""
        f = center - eye
        f = f / np.linalg.norm(f)
        
        s = np.cross(f, up)
        s = s / np.linalg.norm(s)
        
        u = np.cross(s, f)
        
        result = np.eye(4, dtype=np.float32)
        result[0, 0] = s[0]
        result[1, 0] = s[1]
        result[2, 0] = s[2]
        result[0, 1] = u[0]
        result[1, 1] = u[1]
        result[2, 1] = u[2]
        result[0, 2] = -f[0]
        result[1, 2] = -f[1]
        result[2, 2] = -f[2]
        result[3, 0] = -np.dot(s, eye)
        result[3, 1] = -np.dot(u, eye)
        result[3, 2] = np.dot(f, eye)
        
        return result
        
    def _perspective(self, fovy: float, aspect: float, near: float, far: float) -> np.ndarray:
        """Create a perspective projection matrix."""
        f = 1.0 / np.tan(fovy / 2.0)
        
        result = np.zeros((4, 4), dtype=np.float32)
        result[0, 0] = f / aspect
        result[1, 1] = f
        result[2, 2] = (far + near) / (near - far)
        result[2, 3] = -1.0
        result[3, 2] = (2.0 * far * near) / (near - far)
        
        return result


class OrbitCamera(Camera):
    """Orbit camera for viewing objects from all angles."""
    
    def __init__(self, target: np.ndarray = None, distance: float = 10.0,
                 aspect_ratio: float = 16/9, fov: float = 45.0,
                 near: float = 0.1, far: float = 1000.0):
        # Initialize at a position relative to target
        if target is None:
            target = np.zeros(3, dtype=np.float32)
        
        super().__init__(target + np.array([0, 0, distance], dtype=np.float32), aspect_ratio)
        
        self.target = target
        self.distance = distance
        self.min_distance = 1.0
        self.max_distance = 100.0
        
        self.fov = fov
        self.near = near
        self.far = far
        
        # Spherical coordinates
        self.azimuth = 0.0  # Horizontal rotation
        self.elevation = 20.0  # Vertical rotation
        
        # Control settings
        self.rotation_speed = 0.5
        self.zoom_speed = 0.1
        self.pan_speed = 0.01
        
        self._update_position()
        
    def update(self, delta_time: float):
        """Update camera state."""
        # Orbit camera typically doesn't need per-frame updates
        pass
        
    def handle_mouse_movement(self, dx: float, dy: float, buttons: dict = None):
        """Handle mouse movement for orbiting."""
        if buttons is None:
            buttons = {}
            
        if buttons.get('left', False):
            # Rotate camera
            self.azimuth -= dx * self.rotation_speed
            self.elevation += dy * self.rotation_speed
            
            # Clamp elevation
            self.elevation = np.clip(self.elevation, -85.0, 85.0)
            
            self._update_position()
            self._needs_update = True
            
        elif buttons.get('middle', False):
            # Pan camera
            right = np.cross(self.position - self.target, self.up)
            right = right / np.linalg.norm(right)
            
            up = np.cross(right, self.position - self.target)
            up = up / np.linalg.norm(up)
            
            self.target += right * dx * self.pan_speed * self.distance
            self.target += up * dy * self.pan_speed * self.distance
            
            self._update_position()
            self._needs_update = True
            
    def handle_scroll(self, delta: float):
        """Handle mouse scroll for zooming."""
        self.distance *= 1.0 - delta * self.zoom_speed
        self.distance = np.clip(self.distance, self.min_distance, self.max_distance)
        
        self._update_position()
        self._needs_update = True
        
    def handle_keyboard(self, keys: dict, delta_time: float):
        """Handle keyboard input."""
        # Orbit camera typically controlled by mouse
        pass
        
    def _update_position(self):
        """Update camera position from spherical coordinates."""
        # Convert spherical to cartesian
        azimuth_rad = np.radians(self.azimuth)
        elevation_rad = np.radians(self.elevation)
        
        x = self.distance * np.cos(elevation_rad) * np.sin(azimuth_rad)
        y = self.distance * np.sin(elevation_rad)
        z = self.distance * np.cos(elevation_rad) * np.cos(azimuth_rad)
        
        self.position = self.target + np.array([x, y, z], dtype=np.float32)
        
    def _update_matrices(self):
        """Update view and projection matrices."""
        # View matrix
        self._view_matrix = self._look_at(self.position, self.target, self.up)
        
        # Projection matrix
        self._projection_matrix = self._perspective(
            np.radians(self.fov),
            self.aspect_ratio,
            self.near,
            self.far
        )
        
        # Combined matrix
        self._view_projection_matrix = self._projection_matrix @ self._view_matrix
        self._needs_update = False
        
    def _look_at(self, eye: np.ndarray, center: np.ndarray, up: np.ndarray) -> np.ndarray:
        """Create a look-at view matrix."""
        f = center - eye
        f = f / np.linalg.norm(f)
        
        s = np.cross(f, up)
        s = s / np.linalg.norm(s)
        
        u = np.cross(s, f)
        
        result = np.eye(4, dtype=np.float32)
        result[0, 0] = s[0]
        result[1, 0] = s[1]
        result[2, 0] = s[2]
        result[0, 1] = u[0]
        result[1, 1] = u[1]
        result[2, 1] = u[2]
        result[0, 2] = -f[0]
        result[1, 2] = -f[1]
        result[2, 2] = -f[2]
        result[3, 0] = -np.dot(s, eye)
        result[3, 1] = -np.dot(u, eye)
        result[3, 2] = np.dot(f, eye)
        
        return result
        
    def _perspective(self, fovy: float, aspect: float, near: float, far: float) -> np.ndarray:
        """Create a perspective projection matrix."""
        f = 1.0 / np.tan(fovy / 2.0)
        
        result = np.zeros((4, 4), dtype=np.float32)
        result[0, 0] = f / aspect
        result[1, 1] = f
        result[2, 2] = (far + near) / (near - far)
        result[2, 3] = -1.0
        result[3, 2] = (2.0 * far * near) / (near - far)
        
        return result