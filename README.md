Infinite Journal
A 3D infinite journal application for creative drawing and note-taking in an unlimited 3D space.
Features

Infinite 3D drawing space
OpenGL-based rendering
Cross-platform support (Windows, macOS, Linux)

Quick Start
Prerequisites

Python 3.8 or higher
OpenGL-compatible graphics card

Installation

Clone the repository:

bashgit clone https://github.com/DylanRayHastings/infinitejournal.git
cd infinitejournal

Create a virtual environment:

bashpython -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

Install dependencies:

bashpip install -r requirements/base.txt
Running the Application
Option 1: Using the run script
bashpython run.py
Option 2: Using the batch/shell scripts

Windows: Double-click run.bat
Unix/macOS: Run ./run.sh (make sure it's executable: chmod +x run.sh)

Option 3: Direct module execution
bashcd src
python -m infinitejournal.main
Option 4: Install and run
bashpip install -e .
infinitejournal
Controls

ESC: Exit application
F11: Toggle fullscreen

Project Structure
infinitejournal/
├── src/
│   └── infinitejournal/
│       ├── backends/      # Rendering backends
│       ├── drawing/       # Drawing tools and models
│       ├── interface/     # UI components
│       ├── storage/       # File storage and formats
│       ├── tools/         # Drawing tools
│       ├── utilities/     # Utility functions
│       ├── world/         # 3D world management
│       ├── config.py      # Configuration
│       └── main.py        # Entry point
├── requirements/          # Dependencies
├── tests/                 # Unit tests
├── docs/                  # Documentation
└── run.py                # Quick start script
Troubleshooting
OpenGL Errors
If you encounter OpenGL-related errors:

Update graphics drivers: Make sure you have the latest graphics drivers installed
Check OpenGL version: The application requires OpenGL 3.3 by default. You can change this in config.py
Install system dependencies:

Ubuntu/Debian: sudo apt-get install libgl1-mesa-dev
Fedora: sudo dnf install mesa-libGL-devel
macOS: OpenGL should be available by default



Black Screen Issues
If you see a black screen but no errors:

This is normal! The application starts with a black screen
Press ESC to exit
Check the logs in the logs/ directory for any issues

Development
Running Tests
bashpytest tests/
Code Style
bashflake8 src/
black src/
License
MIT License - see LICENSE file for details
Contributing
See CONTRIBUTING.md for contribution guidelines.