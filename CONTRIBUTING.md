# Contributing to Infinite Journal

First off, thank you for considering contributing to Infinite Journal!

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [How Can I Contribute?](#how-can-i-contribute)
- [Development Process](#development-process)
- [Style Guidelines](#style-guidelines)
- [Commit Guidelines](#commit-guidelines)
- [Pull Request Process](#pull-request-process)
- [Community](#community)

## Code of Conduct

This project and everyone participating in it is governed by our Code of Conduct. By participating, you are expected to uphold this code. Please be respectful and constructive in all interactions.

## Getting Started

### Prerequisites

- Python 3.8 or higher
- OpenGL-compatible graphics card
- Git
- A GitHub account

### Setting Up Your Development Environment

1. **Fork the repository**
   ```bash
   # Click the 'Fork' button on GitHub
   ```

2. **Clone your fork**
   ```bash
   git clone https://github.com/DylanRayHastings/infinitejournal.git
   cd infinitejournal
   ```

3. **Add upstream remote**
   ```bash
   git remote add upstream https://github.com/originalowner/infinitejournal.git
   ```

4. **Create a virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

5. **Install development dependencies**
   ```bash
   pip install -e ".[dev]"
   ```

6. **Install pre-commit hooks**
   ```bash
   pre-commit install
   ```

7. **Run the diagnostic tool**
   ```bash
   python diagnostic.py
   ```

8. **Run tests to ensure everything is working**
   ```bash
   pytest
   ```

## How Can I Contribute?

### Reporting Bugs

Before creating bug reports, please check existing issues to avoid duplicates. When you create a bug report, include as many details as possible:

**Bug Report Template:**
```markdown
### Description
[Clear and concise description of the bug]

### Steps to Reproduce
1. [First step]
2. [Second step]
3. [...]

### Expected Behavior
[What you expected to happen]

### Actual Behavior
[What actually happened]

### Environment
- OS: [e.g., Windows 10, Ubuntu 22.04, macOS 13]
- Python version: [e.g., 3.11.0]
- Infinite Journal version: [e.g., 0.1.0]
- Graphics card: [e.g., NVIDIA GTX 1060]
- OpenGL version: [from diagnostic tool]

### Additional Context
[Any other relevant information, error messages, screenshots]
```

### Suggesting Enhancements

Enhancement suggestions are tracked as GitHub issues. When creating an enhancement suggestion, include:

**Enhancement Template:**
```markdown
### Feature Description
[Clear description of the proposed feature]

### Use Case
[Explain how this feature would be used and who would benefit]

### Proposed Implementation
[Optional: Your ideas on how to implement this]

### Alternatives Considered
[Optional: Other solutions you've thought about]

### Additional Context
[Mockups, examples, or references]
```

### Contributing Code

#### Finding Issues to Work On

- Look for issues labeled `good first issue` for beginner-friendly tasks
- Check issues labeled `help wanted` for areas where we need assistance
- Feel free to ask questions on any issue you're interested in

#### Before You Start Coding

1. **Check if someone is already working on it**
   - Look for assigned issues or recent comments
   - Comment on the issue to express your interest

2. **Discuss major changes**
   - For significant changes, open an issue first
   - Get feedback on your approach before investing time

3. **Keep your fork updated**
   ```bash
   git checkout main
   git fetch upstream
   git merge upstream/main
   ```

## Development Process

### 1. Create a Feature Branch

```bash
git checkout -b feature/your-feature-name
# or
git checkout -b fix/issue-number-description
```

### 2. Make Your Changes

- Write clean, readable code
- Add tests for new functionality
- Update documentation as needed
- Follow the style guidelines

### 3. Test Your Changes

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_specific.py

# Run with coverage
pytest --cov=infinitejournal

# Run linting
flake8 src/
mypy src/
black --check src/
isort --check-only src/
```

### 4. Commit Your Changes

Follow our commit message conventions (see [Commit Guidelines](#commit-guidelines))

### 5. Push to Your Fork

```bash
git push origin feature/your-feature-name
```

### 6. Create a Pull Request

- Use the PR template
- Link related issues
- Ensure all checks pass

## Style Guidelines

### Python Style

We follow PEP 8 with some modifications:
- Line length: 100 characters
- Use Black for formatting
- Use isort for import ordering

### Code Style Examples

```python
# Good: Clear variable names
player_position = Vector3(x=0, y=0, z=0)

# Bad: Unclear abbreviations
pp = V3(0, 0, 0)

# Good: Type hints
def calculate_distance(point_a: Vector3, point_b: Vector3) -> float:
    """Calculate Euclidean distance between two points."""
    return (point_b - point_a).magnitude()

# Good: Docstrings (Google style)
def render_stroke(stroke: Stroke, camera: Camera) -> None:
    """Render a stroke to the screen.
    
    Args:
        stroke: The stroke to render
        camera: Current camera for view transformation
        
    Raises:
        RenderError: If the stroke cannot be rendered
    """
    pass
```

### Directory Structure

```
src/infinitejournal/
├── module/
│   ├── __init__.py      # Public API exports
│   ├── core.py          # Core functionality
│   ├── models.py        # Data models
│   ├── utils.py         # Helper functions
│   └── tests/
│       ├── __init__.py
│       └── test_core.py
```

### Testing Guidelines

- Write tests for all new functionality
- Aim for >80% code coverage
- Use descriptive test names
- Follow the Arrange-Act-Assert pattern

```python
def test_stroke_creation_with_valid_points():
    """Test that a stroke can be created with valid points."""
    # Arrange
    points = [Point(0, 0, 0), Point(1, 1, 1)]
    
    # Act
    stroke = Stroke(points)
    
    # Assert
    assert len(stroke.points) == 2
    assert stroke.points[0] == Point(0, 0, 0)
```

## Commit Guidelines

We follow [Conventional Commits](https://www.conventionalcommits.org/):

### Format
```
<type>(<scope>): <subject>

<body>

<footer>
```

### Types
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation only changes
- `style`: Code style changes (formatting, missing semicolons, etc)
- `refactor`: Code change that neither fixes a bug nor adds a feature
- `perf`: Performance improvements
- `test`: Adding missing tests or correcting existing tests
- `build`: Changes that affect the build system or external dependencies
- `ci`: Changes to CI configuration files and scripts
- `chore`: Other changes that don't modify src or test files

### Examples
```
feat(drawing): add pressure sensitivity to brush tool

Implement pressure sensitivity for stylus input devices.
This allows for more natural drawing with varying line weights.

Closes #123
```

```
fix(renderer): prevent memory leak in stroke rendering

The stroke vertex buffer was not being properly released,
causing memory usage to increase over time.
```

## Pull Request Process

1. **Ensure your PR is ready**
   - All tests pass
   - Code follows style guidelines
   - Documentation is updated
   - Commit messages follow conventions

2. **Fill out the PR template**
   ```markdown
   ## Description
   [Describe your changes]
   
   ## Type of Change
   - [ ] Bug fix
   - [ ] New feature
   - [ ] Breaking change
   - [ ] Documentation update
   
   ## Testing
   - [ ] Tests pass locally
   - [ ] New tests added
   - [ ] Manual testing completed
   
   ## Checklist
   - [ ] My code follows the style guidelines
   - [ ] I have performed a self-review
   - [ ] I have commented my code where necessary
   - [ ] I have updated the documentation
   - [ ] My changes generate no new warnings
   ```

3. **Respond to review feedback**
   - Address all comments
   - Push fixes as new commits (don't force-push during review)
   - Mark conversations as resolved when addressed

4. **After approval**
   - Squash commits if requested
   - Ensure branch is up to date with main

## Community

### Getting Help

- **GitHub Issues**: For bugs and feature requests
- **Discussions**: For general questions and ideas
- **Wiki**: For documentation and guides

### Ways to Contribute Beyond Code

- **Documentation**: Help improve our docs
- **Testing**: Test on different platforms and report issues
- **Design**: Contribute UI/UX designs and mockups
- **Translation**: Help translate the application
- **Community**: Help answer questions and welcome newcomers

## Recognition

Contributors will be recognized in:
- The CONTRIBUTORS.md file
- Release notes
- Project documentation

Thank you for contributing to Infinite Journal! 🎨✨