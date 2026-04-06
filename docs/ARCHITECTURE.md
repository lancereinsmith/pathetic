# Architecture Overview

This document provides an overview of the pathetic-cli codebase structure and design decisions.

## Project Structure

```text
pathetic-cli/
├── pathetic.py          # Main CLI application (single-file)
├── tests/               # Test suite
│   ├── __init__.py
│   ├── conftest.py      # Pytest fixtures
│   └── test_pathetic.py # Test cases
├── docs/                # Documentation
├── .github/
│   └── workflows/
│       └── ci.yml       # CI/CD pipeline
├── pyproject.toml       # Project configuration and dependencies
└── README.md            # User documentation
```

## Core Components

### 1. Section Rendering Functions

Each information section has its own rendering function:

- `section_cwd_home()` - Current working directory and home
- `section_system()` - System platform and user's active Python info
- `section_paths()` - PATH entries with source tracing and executable counts
- `section_python_path()` - Python sys.path
- `section_env()` - All environment variables grouped by category
- `section_fs()` - Filesystem statistics
- `section_git()` - Git repository information

These functions return Rich `Panel` objects for consistent formatting. `section_env()` returns a list of panels (one per category).

### 2. PATH Source Tracing

`trace_path_sources()` maps each PATH entry to the config file that set it:

- `/etc/paths` and `/etc/paths.d/*` — macOS system paths
- Shell config files (`~/.zshrc`, `~/.zprofile`, `~/.bashrc`, etc.) — user PATH exports
- Sourced files (e.g., `~/.cargo/env` sourced from `~/.zshenv`) — followed recursively
- Well-known eval patterns (`brew shellenv`, OrbStack init)
- Runtime sources (venv activation, VS Code, iTerm.app)

`_count_executables()` counts executable files in each PATH directory, showing `missing` for nonexistent directories.

### 3. User Python Detection

`get_user_python()` finds the Python the user has active on their PATH, skipping this tool's own isolated venv. This matters when installed via `uv tool install`.

### 4. Environment Variable Categorization

`categorize_env_var()` classifies each env var into a category (Shell, Python, Git, Cloud, Docker, CI/CD, etc.) using exact-match and prefix-match tables. `get_grouped_env_vars()` returns all env vars organized by category.

### 5. Environment Detection

`detect_virtual_environment()` detects active Python environments:

- Virtualenv/venv (via `VIRTUAL_ENV` or `sys.prefix` heuristic)
- Conda (via `CONDA_PREFIX`)
- Poetry (via `POETRY_ACTIVE`)
- Pipenv (via `PIPENV_ACTIVE`)
- PDM (via `PDM_PROJECT_ROOT`)
- uv (via `UV_PYTHON` or `UV_CACHE_DIR`)

### 6. Configuration

The `Config` dataclass encapsulates all CLI options: `show_all`, `show_env`, `show_fs`, `limit`, `as_json`, `env_keys`.

### 7. Output Formats

- **Text** (default): Rich-formatted panels in a responsive columnar grid
- **JSON** (`--json`): Machine-readable structured data via `click.echo()`

### 8. Responsive Layout

`render_output()` arranges panels based on terminal width:

- **Compact panels** (Location, System, Git, FS): laid out in a `Table.grid()` — 3 columns at ≥140 chars, 2 at ≥90, 1 otherwise
- **Wide panels** (PATH, Python Path, Environment): always full width

## Data Flow

1. **CLI Entry Point**: `main()` receives Click arguments
2. **Config Creation**: Arguments packaged into `Config` dataclass
3. **Format Decision**: JSON via `build_json_output()`, or text via `render_output()`
4. **Data Collection**: Section functions gather system info, trace PATH sources, categorize env vars
5. **Rendering**: Panels arranged in responsive grid and printed

## Error Handling

- Subprocess calls (git, python version) use timeouts and graceful fallbacks
- File system operations handle permission errors per-file (e.g., `os.scandir` skips inaccessible entries)
- Missing directories in PATH shown as `missing` rather than crashing
- Sourced file tracing handles missing/unreadable files gracefully

## Testing Strategy

- **Unit tests**: Individual functions (categorization, path tracing, config creation)
- **Integration tests**: CLI command execution via Click's `CliRunner`
- **Mocking**: External dependencies (git, file system) mocked via pytest fixtures
- **Fixtures**: Common test data in `conftest.py`
