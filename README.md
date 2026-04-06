# pathetic

A colorful, fast CLI to inspect your current environment: locations, system info, PATH with source tracing, Python environment, grouped environment variables, filesystem usage, and Git status. Built with Rich for delightful output and Click for a clean command-line UX.

## Highlights

- Visual, readable output with sensible defaults
- Responsive columnar layout that adapts to terminal width
- PATH entries traced back to their source file (.zshrc, /etc/paths, etc.)
- Shows the user's active Python, not the tool's isolated environment
- All environment variables grouped by category (Shell, Python, Git, Cloud, etc.)

## Requirements

- Python >= 3.11

## Installation

Install locally (editable) while developing:

```bash
uv pip install -e .
```

Or install globally with `uv tool`:

```bash
uv tool install pathetic-cli
```

This exposes the `ptc` command.

## Quickstart

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

Focused views:

```bash
ptc --env                              # All env vars, grouped by category
ptc --fs                               # File system stats
ptc --env-key HOME --env-key EDITOR    # Specific env vars only
ptc --all --limit 50                   # More PATH/sys.path rows
```

## CLI Options

```text
ptc [OPTIONS]

Options:
  -h, --help         Show this message and exit
  --version          Show version
  --all              Show all sections
  --env              Show environment variables (grouped)
  --fs               Show file system stats
  --limit INTEGER    Max rows for PATH and sys.path (default: 25)
  --json             Output as JSON (machine-readable)
  --env-key TEXT     Show specific env vars (repeatable)
```

## What the tool shows

- **Location**: Current working directory and home directory
- **System**: Platform, user's active Python version, architecture, executable
- **Environment detection**: Active virtualenv/conda/uv info shown prominently
- **PATH**: First N entries with source file origin and executable count (configurable with `--limit`)
- **Python Path**: First N entries of `sys.path` (shown with `--all`)
- **Environment**: All variables grouped by category (`--env` or `--all`)
- **File System**: Total, free, used, and usage percent (`--fs` or `--all`)
- **Git**: Branch, short commit, working state (auto-detected when in a repo)

## Design philosophy

- Defaults show the most useful, actionable info quickly
- Additional details are opt-in via flags
- Clean typography and responsive layout with Rich
- PATH source tracing helps debug environment issues

## Development

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

## Troubleshooting

- Command not found after install: ensure your Python user base or pipx bin directory is on PATH.
- Missing colors or odd glyphs: use a modern terminal with UTF-8 and TrueColor support.

## License

MIT. See `LICENSE`.
