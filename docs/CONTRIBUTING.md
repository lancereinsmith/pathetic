# Contributing to pathetic-cli

Thank you for your interest in contributing to pathetic-cli! This document provides guidelines and instructions for contributing.

## Development Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/lancereinsmith/pathetic.git
   cd pathetic
   ```

2. **Install dependencies**
   ```bash
   uv pip install -e ".[dev]"
   ```

3. **Install pre-commit hooks** (optional but recommended)
   ```bash
   pre-commit install
   ```

## Development Workflow

1. **Create a branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes**
   - Write code following the existing style
   - Add tests for new functionality
   - Update documentation as needed

3. **Run tests**
   ```bash
   uv run pytest tests/ -v
   ```

4. **Run linting and formatting**
   ```bash
   uv run ruff check .
   uv run ruff format .
   uv run mypy pathetic.py
   ```

5. **Commit your changes**
   ```bash
   git add .
   git commit -m "Description of your changes"
   ```
   Pre-commit hooks will run automatically if installed.

6. **Push and create a pull request**
   ```bash
   git push origin feature/your-feature-name
   ```

## Code Style

- Follow PEP 8 style guidelines
- Use `ruff` for linting and formatting (configuration in `pyproject.toml`)
- Use type hints where possible
- Add docstrings to all public functions and classes
- Keep functions focused and small

## Testing

- Write tests for all new features
- Aim for high test coverage
- Use pytest fixtures for common setup
- Mock external dependencies (subprocess, file system, etc.)

## Documentation

- Update README.md for user-facing changes
- Add docstrings to new functions and classes
- Update this CONTRIBUTING.md if workflow changes

## Pull Request Process

1. Ensure all tests pass
2. Ensure linting passes (`ruff check .`)
3. Ensure formatting is correct (`ruff format .`)
4. Update documentation as needed
5. Write a clear PR description explaining your changes

## Questions?

Feel free to open an issue for questions or discussions!
