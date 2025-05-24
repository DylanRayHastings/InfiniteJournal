"""Setup script for Infinite Journal."""

from setuptools import setup, find_packages
from pathlib import Path

# Read README
readme_path = Path(__file__).parent / "README.md"
long_description = readme_path.read_text() if readme_path.exists() else ""

# Read requirements
requirements_path = Path(__file__).parent / "requirements" / "base.txt"
requirements = []
if requirements_path.exists():
    requirements = [line.strip() for line in requirements_path.read_text().splitlines() 
                    if line.strip() and not line.startswith("#")]

setup(
    name="infinitejournal",
    version="1.0.2",
    author="Dilly",
    author_email="HastingsDylanR@gmail.com",
    description="A 3D infinite journal application",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/DylanRayHastings/infinitejournal",
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: End Users/Desktop",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.8",
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "infinitejournal=infinitejournal.main:main",
        ],
    },
)