# Architecture Overview

This document provides an overview of the pathetic-cli codebase structure and design decisions.

## Project Structure

```
pathetic-cli/
├── pathetic.py          # Main CLI application
├── tests/               # Test suite
│   ├── __init__.py
│   ├── conftest.py      # Pytest fixtures
│   └── test_pathetic.py # Test cases
├── .github/
│   └── workflows/
│       └── ci.yml       # CI/CD pipeline
├── pyproject.toml       # Project configuration and dependencies
└── README.md           # User documentation
```

## Core Components

### 1. Section Rendering Functions

Each information section has its own rendering function:

- `section_cwd_home()` - Current working directory and home
- `section_system()` - System platform and Python info
- `section_paths()` - PATH environment variable
- `section_python_path()` - Python sys.path
- `section_env()` - Selected environment variables
- `section_fs()` - Filesystem statistics
- `section_git()` - Git repository information

These functions return Rich `Panel` objects for consistent formatting.

### 2. Environment Detection

The `detect_virtual_environment()` function detects active Python environments:

- Virtualenv/venv (via `VIRTUAL_ENV` or `sys.prefix` heuristic)
- Conda (via `CONDA_PREFIX`)
- Poetry (via `POETRY_ACTIVE`)
- Pipenv (via `PIPENV_ACTIVE`)
- PDM (via `PDM_PROJECT_ROOT`)
- uv (via `UV_PYTHON` or `UV_CACHE_DIR`)

### 3. Configuration

The `Config` dataclass encapsulates all CLI options, making it easy to pass configuration around and test.

### 4. Output Formats

The tool supports multiple output formats:

- **Text** (default): Rich-formatted panels for terminal display
- **JSON**: Machine-readable structured data
- **YAML**: Alternative structured format (requires `pyyaml`)
- **TOML**: Alternative structured format (requires `tomli-w`)

### 5. Data Building

- `build_json_output()`: Constructs the complete data structure for export formats
- `build_panels()`: Constructs the list of panels for text output

## Design Decisions

### Why Rich?

Rich provides beautiful terminal output with minimal code. It handles:
- Colors and styling
- Tables and panels
- Cross-platform compatibility
- Automatic terminal detection

### Why Click?

Click provides a clean, declarative API for CLI argument parsing with:
- Type validation
- Help text generation
- Consistent interface

### Why Separate Section Functions?

- **Modularity**: Each section can be tested independently
- **Reusability**: Sections can be combined in different ways
- **Maintainability**: Changes to one section don't affect others

### Why Config Dataclass?

- **Type safety**: All options are typed
- **Testability**: Easy to create test configurations
- **Clarity**: Single source of truth for all options

## Data Flow

1. **CLI Entry Point**: `main()` function receives Click arguments
2. **Config Creation**: Arguments are packaged into `Config` dataclass
3. **Format Decision**: Based on `as_json`, `as_yaml`, or `as_toml` flags
4. **Data Collection**: Either `build_json_output()` or `build_panels()` is called
5. **Rendering**: Data is formatted and printed to console

## Error Handling

- Subprocess calls (git) use timeouts and graceful fallbacks
- File system operations handle permission errors
- Missing optional dependencies show helpful error messages
- Invalid configurations are caught early with clear messages

## Testing Strategy

- **Unit tests**: Test individual functions in isolation
- **Integration tests**: Test CLI command execution
- **Mocking**: External dependencies (git, file system) are mocked
- **Fixtures**: Common test data is provided via pytest fixtures

## Future Considerations

- Configuration file support (saved preferences)
- Plugin system for custom sections
- Caching for expensive operations
- More export formats if needed
