# diagnostic.py - Check system compatibility for Infinite Journal

import sys
import platform

print("=== Infinite Journal System Diagnostic ===\n")

# Check Python version
print(f"Python Version: {sys.version}")
python_version = sys.version_info
if python_version.major < 3 or (python_version.major == 3 and python_version.minor < 8):
    print(" Python 3.8 or higher is required!")
else:
    print(" Python version is compatible")

# Check platform
print(f"\nPlatform: {platform.system()} {platform.release()}")
print(f"Architecture: {platform.machine()}")

# Check required modules
print("\nChecking required modules:")
modules_to_check = [
    ("pygame", "2.5.0"),
    ("OpenGL", "3.1.6"),
    ("numpy", "1.24.0"),
]

all_modules_ok = True
for module_name, min_version in modules_to_check:
    try:
        module = __import__(module_name)
        version = getattr(module, "__version__", "Unknown")
        print(f" {module_name}: {version}")
    except ImportError:
        print(f" {module_name}: Not installed")
        all_modules_ok = False

if not all_modules_ok:
    print("\n  Some required modules are missing!")
    print("Run: pip install -r requirements/base.txt")

# Test OpenGL initialization
print("\nTesting OpenGL initialization...")
try:
    import pygame
    from OpenGL.GL import *
    
    pygame.init()
    pygame.display.set_mode((1, 1), pygame.OPENGL | pygame.HIDDEN)
    
    gl_version = glGetString(GL_VERSION)
    gl_vendor = glGetString(GL_VENDOR)
    gl_renderer = glGetString(GL_RENDERER)
    
    if gl_version:
        print(f" OpenGL Version: {gl_version.decode()}")
        print(f"   Vendor: {gl_vendor.decode()}")
        print(f"   Renderer: {gl_renderer.decode()}")
    else:
        print(" Could not get OpenGL version")
    
    pygame.quit()
    
except Exception as e:
    print(f" OpenGL initialization failed: {e}")
    print("   Make sure you have proper graphics drivers installed")

print("\n=== Diagnostic Complete ===")
print("\nIf all checks passed, you should be able to run Infinite Journal!")
print("Run: python run.py")