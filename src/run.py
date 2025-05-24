#!/usr/bin/env python
# run.py - Quick start script for Infinite Journal

import sys
import os
from pathlib import Path

# Add src directory to Python path
src_dir = Path(__file__).parent / "src"
sys.path.insert(0, str(src_dir))

# Import and run main
from infinitejournal.main import main

if __name__ == "__main__":
    main()