# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.2.1] - 2025-12-19

### Fixed
- Fixed test failures in CI environment related to UV environment variable detection
- Fixed mypy type checking errors
- Fixed CI workflow to use `uv sync` instead of `uv pip install`
- Updated ruff configuration to use new `[tool.ruff.lint]` section structure

### Changed
- Updated dependency management to use PEP 735 dependency groups
- Switched build backend from setuptools to hatchling for better dependency group support

## [0.2.0] - 2025-12-19

### Added
- Cross-platform PATH separator support (Windows compatibility)
- Enhanced environment detection (Poetry, Pipenv, PDM)
- PATH filtering (`--path-filter`) and exclusion (`--path-exclude`) options
- YAML export format (`--yaml`)
- TOML export format (`--toml`)
- Tree depth and max-items configuration (`--tree-depth`, `--tree-max-items`)
- Additional environment variable groups (docker, cloud, editor, proxy)
- `--version` flag
- Comprehensive test suite
- GitHub Actions CI/CD pipeline
- Pre-commit hooks
- Development documentation
- Improved error handling with timeouts for subprocess calls
- Better type hints and docstrings throughout

### Changed
- Refactored `main()` function into smaller, testable components
- Improved subprocess error handling with timeouts
- Enhanced virtual environment detection logic
- Version now read from `pyproject.toml` as single source of truth

### Fixed
- PATH separator now uses `os.pathsep` for cross-platform compatibility
- Better error messages when optional dependencies are missing

## [0.1.1] - Initial Release

### Added
- Basic system information display
- PATH and Python path visualization
- Environment variable display
- Filesystem statistics
- Git repository information
- Directory tree view
- JSON export format
- Rich terminal formatting
