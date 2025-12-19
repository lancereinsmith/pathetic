## pathetic

A colorful, fast CLI to inspect your current environment: locations, system info, PATH, Python paths, selected environment variables, filesystem usage, Git status, and a small directory tree. Built with Rich for delightful output and Click for a clean command-line UX.

### Highlights

- Visual, readable output with sensible defaults
- Modular sections you can toggle on/off
- Zero-config quick overview; add flags when you want more detail

### Requirements

- Python >= 3.11

### Installation

Install locally (editable) while developing:

```bash
uv pip install -e .
```

Or install globally with `uv tool`:

```bash
uv tool install pathetic-cli
```

This exposes the `ptc` command.

### Quickstart

Run the default, concise snapshot:

```bash
ptc
```

Show everything:

```bash
ptc --all
```

Machine-readable output:

```bash
ptc --json --all > snapshot.json
```

Increase list sizes for PATH and sys.path:

```bash
ptc --all --limit 25
```

Focused views:

```bash
ptc --env        # Selected environment variables
ptc --fs         # File system stats
ptc --tree       # Small directory tree (depth 2)
ptc --env-group python --env-key FOO --env-key BAR  # Custom env selection
```

### CLI Options

```bash
ptc [OPTIONS]

Options:
  -h, --help              Show this message and exit
  --all                   Show all sections
  --no-paths              Hide PATH section
  --no-python-path        Hide sys.path section
  --env                   Show selected environment variables
  --fs                    Show file system stats
  --tree                  Show a small directory tree
  --limit INTEGER         Max rows for PATH and sys.path (default: 10)
  --json                  Output as JSON (machine-readable)
  --env-group [ci|common|python]
                          Predefined env var groups (repeatable)
  --env-key TEXT          Additional environment variable keys (repeatable)
```

### What the tool shows

- Location: Current working directory and home directory
- System: Platform, Python version/implementation, architecture, executable
- Environment detection: Active virtualenv/conda/uv info shown prominently
- PATH: First N entries (configurable with `--limit`)
- Python Path: First N entries of `sys.path` (shown with `--all`)
- Environment: Selected high-signal variables (`--env` to show)
- File System: Total, free, used, and usage percent (`--fs`)
- Git: Branch, short commit, working state (auto-detected when in a repo)
- Tree: Small directory tree of the current directory (`--tree`)

### Design philosophy

- Defaults show the most useful, actionable info quickly
- Additional details are opt-in via flags
- Clean typography and layout with Rich

### Development

Install dev dependencies and run locally:

```bash
uv pip install -e .
ptc --all
```

Project entry point is defined in `pyproject.toml`:

```toml
[project.scripts]
ptc = "pathetic:main"
```

Source code: `pathetic.py` uses small, focused rendering functions for each section and a Click command to wire options:

- `section_cwd_home()`
- `section_system()`
- `section_paths()`
- `section_python_path()`
- `section_env()`
- `section_fs()`
- `section_git()`

### Troubleshooting

- Command not found after install: ensure your Python user base or pipx bin directory is on PATH.
- Missing colors or odd glyphs: use a modern terminal with UTF-8 and TrueColor support.

### License

MIT. See `LICENSE`.
