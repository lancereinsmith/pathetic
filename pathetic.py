#!/usr/bin/env python3
"""A colorful CLI to inspect system, environment, and PATH information."""

import json
import os
import platform
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import click
from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

# Try to import optional dependencies
try:
    import tomllib  # Python 3.11+
except ImportError:
    try:
        import tomli as tomllib  # type: ignore[no-redef]
    except ImportError:
        tomllib = None  # type: ignore[assignment]

try:
    import yaml
except ImportError:
    yaml = None


# Version from pyproject.toml (single source of truth)
def _get_version() -> str:
    """Read version from pyproject.toml."""
    try:
        # Try reading from installed package first
        import importlib.metadata

        return importlib.metadata.version("pathetic-cli")
    except Exception:
        # Fallback: read directly from pyproject.toml
        try:
            pyproject_path = Path(__file__).parent / "pyproject.toml"
            if pyproject_path.exists():
                if tomllib:
                    with open(pyproject_path, "rb") as f:
                        data = tomllib.load(f)
                        version: str = str(data.get("project", {}).get("version", ""))
                        return version
                else:
                    # Fallback: simple regex if tomllib not available
                    import re

                    content = pyproject_path.read_text()
                    match = re.search(r'version\s*=\s*"([^"]+)"', content)
                    if match:
                        return match.group(1)
        except Exception:
            pass
    return "0.0.0"  # Last resort fallback


__version__ = _get_version()


def render_header(console: Console) -> None:
    """Render the header for the CLI output."""
    console.print("\n[bold blue]🔎 System Snapshot[/bold blue]\n")


def section_cwd_home() -> Panel:
    """Render a panel showing current working directory and home directory.

    Returns:
        A Rich Panel containing CWD and home directory information.
    """
    text = Text()
    text.append("📁 CWD: ", style="bold")
    text.append(f"{os.getcwd()}\n", style="green")
    text.append("🏠 Home: ", style="bold")
    text.append(f"{os.path.expanduser('~')}", style="blue")
    return Panel(text, title="Location", border_style="green", padding=(1, 2))


def section_system() -> Panel:
    """Render a panel showing system information.

    Returns:
        A Rich Panel containing platform, Python version, architecture, and executable info.
    """
    info = Text()
    info.append("🖥️ Platform: ", style="bold")
    info.append(f"{platform.system()} {platform.release()}\n", style="cyan")
    info.append("🐍 Python: ", style="bold")
    info.append(
        f"{platform.python_version()} ({platform.python_implementation()})\n",
        style="green",
    )
    info.append("🏗️ Arch: ", style="bold")
    info.append(f"{platform.machine()}\n", style="blue")
    info.append("📦 Executable: ", style="bold")
    info.append(f"{sys.executable}", style="magenta")
    return Panel(info, title="System", border_style="cyan", padding=(1, 2))


def section_paths(
    limit: int = 10,
    path_filter: str | None = None,
    path_exclude: str | None = None,
) -> Panel:
    """Render a panel showing PATH entries.

    Args:
        limit: Maximum number of PATH entries to display.
        path_filter: Optional filter to include only PATH entries containing this text.
        path_exclude: Optional filter to exclude PATH entries containing this text.

    Returns:
        A Rich Panel containing PATH information in a table format.
    """
    parts = os.environ.get("PATH", "").split(os.pathsep)

    # Apply filters
    if path_filter:
        parts = [p for p in parts if path_filter.lower() in p.lower()]
    if path_exclude:
        parts = [p for p in parts if path_exclude.lower() not in p.lower()]

    table = Table(
        title=f"PATH (first {min(limit, len(parts))} of {len(parts)})",
        box=box.ROUNDED,
    )
    table.add_column("#", style="cyan", no_wrap=True)
    table.add_column("Path", style="white")
    for i, p in enumerate(parts[:limit], 1):
        # Highlight filtered entries
        path_display = p or "[dim]<empty>[/dim]"
        if path_filter and path_filter.lower() in p.lower():
            path_display = f"[yellow]{path_display}[/yellow]"
        table.add_row(str(i), path_display)
    return Panel(table, title="PATH", border_style="yellow", padding=(1, 1))


def section_python_path(limit: int = 10) -> Panel:
    """Render a panel showing Python sys.path entries.

    Args:
        limit: Maximum number of sys.path entries to display.

    Returns:
        A Rich Panel containing Python path information in a table format.
    """
    table = Table(
        title=f"sys.path (first {min(limit, len(sys.path))} of {len(sys.path)})",
        box=box.ROUNDED,
    )
    table.add_column("#", style="magenta", no_wrap=True)
    table.add_column("Path", style="white")
    for i, p in enumerate(sys.path[:limit], 1):
        table.add_row(str(i), p)
    return Panel(table, title="Python Path", border_style="green", padding=(1, 1))


ENV_GROUPS: dict[str, list[str]] = {
    # Common, high-signal variables
    "common": [
        "USER",
        "SHELL",
        "LANG",
        "PWD",
        "HOME",
        "TMPDIR",
        "LOGNAME",
    ],
    # Python and tooling related
    "python": [
        "PYTHONPATH",
        "VIRTUAL_ENV",
        "CONDA_PREFIX",
        "PIPX_HOME",
        "PIPX_BIN_DIR",
        "UV_CACHE_DIR",
        "UV_PYTHON",
    ],
    # CI environments
    "ci": [
        "CI",
        "GITHUB_ACTIONS",
        "GITLAB_CI",
        "BUILDKITE",
        "CIRCLECI",
        "APPVEYOR",
        "TRAVIS",
    ],
    # Docker-related
    "docker": [
        "DOCKER_HOST",
        "DOCKER_TLS_VERIFY",
        "DOCKER_CERT_PATH",
        "COMPOSE_PROJECT_NAME",
    ],
    # Cloud providers
    "cloud": [
        "AWS_REGION",
        "AWS_PROFILE",
        "GCP_PROJECT",
        "AZURE_SUBSCRIPTION_ID",
        "GOOGLE_APPLICATION_CREDENTIALS",
    ],
    # Editor-related
    "editor": [
        "EDITOR",
        "VISUAL",
        "GIT_EDITOR",
    ],
    # Proxy settings
    "proxy": [
        "HTTP_PROXY",
        "HTTPS_PROXY",
        "http_proxy",
        "https_proxy",
        "NO_PROXY",
        "no_proxy",
    ],
}


def section_env(keys: list[str] | None = None) -> Panel:
    """Render a panel showing selected environment variables.

    Args:
        keys: List of environment variable keys to display. If None, uses common group.

    Returns:
        A Rich Panel containing environment variable information in a table format.
    """
    table = Table(title="Selected Environment", box=box.ROUNDED)
    table.add_column("Variable", style="cyan", no_wrap=True)
    table.add_column("Value", style="white")
    if not keys:
        keys = ENV_GROUPS["common"]
    for k in keys:
        v = os.environ.get(k, "[dim]Not set[/dim]")
        sv = str(v)
        if len(sv) > 80:
            sv = sv[:77] + "..."
        table.add_row(k, sv)
    return Panel(table, title="Environment", border_style="blue", padding=(1, 1))


def section_fs() -> Panel:
    """Render a panel showing filesystem statistics.

    Returns:
        A Rich Panel containing filesystem usage information, or an error message if unavailable.
    """
    try:
        statvfs = os.statvfs(".")
    except (OSError, AttributeError):
        return Panel("Unavailable", title="File System", border_style="red")

    def fmt(b: float) -> str:
        """Format bytes into human-readable format."""
        for u in ["B", "KB", "MB", "GB", "TB", "PB"]:
            if b < 1024.0:
                return f"{b:.1f} {u}"
            b /= 1024.0
        return f"{b:.1f} EB"

    total = statvfs.f_frsize * statvfs.f_blocks
    free = statvfs.f_frsize * statvfs.f_bavail
    used = total - free
    usage_percent = (used / total) * 100 if total else 0.0

    info = Text()
    info.append("💾 Total: ", style="bold")
    info.append(f"{fmt(total)}\n", style="green")
    info.append("🆓 Free: ", style="bold")
    info.append(f"{fmt(free)}\n", style="blue")
    info.append("📊 Used: ", style="bold")
    info.append(f"{fmt(used)}\n", style="red")
    info.append("📈 Usage: ", style="bold")
    info.append(f"{usage_percent:.1f}%", style="yellow")
    return Panel(info, title="File System", border_style="red", padding=(1, 2))


def get_git_info(timeout: float = 5.0) -> dict[str, Any] | None:
    """Get git information with timeout and better error handling.

    Args:
        timeout: Maximum time to wait for git commands in seconds.

    Returns:
        Dictionary with branch, commit, and changes count, or None if git is unavailable.
    """
    try:
        branch = subprocess.check_output(
            ["git", "branch", "--show-current"],
            stderr=subprocess.DEVNULL,
            text=True,
            timeout=timeout,
        ).strip()
        commit = subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            stderr=subprocess.DEVNULL,
            text=True,
            timeout=timeout,
        ).strip()
        status = subprocess.check_output(
            ["git", "status", "--porcelain"],
            stderr=subprocess.DEVNULL,
            text=True,
            timeout=timeout,
        ).strip()
        return {
            "branch": branch,
            "commit": commit,
            "changes": len(status.splitlines()) if status else 0,
        }
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
        return None


def section_git(timeout: float = 5.0) -> Panel | None:
    """Render a panel showing git repository information.

    Args:
        timeout: Maximum time to wait for git commands in seconds.

    Returns:
        A Rich Panel containing git information, or None if not in a git repo or git unavailable.
    """
    git_info = get_git_info(timeout=timeout)
    if git_info is None:
        return None

    info = Text()
    info.append("🌿 Branch: ", style="bold")
    info.append(f"{git_info['branch']}\n", style="green")
    info.append("📝 Commit: ", style="bold")
    info.append(f"{git_info['commit']}\n", style="blue")
    info.append("📋 Status: ", style="bold")
    info.append(
        f"{git_info['changes']} changes" if git_info["changes"] > 0 else "Clean",
        style="yellow",
    )
    return Panel(info, title="Git", border_style="green", padding=(1, 2))


def detect_virtual_environment() -> dict[str, str | None]:
    """Detect and return information about the active Python environment.

    Detects virtualenv/venv, conda, Poetry, Pipenv, PDM, and uv environments.

    Returns:
        Dictionary containing:
        - manager: Environment manager name (e.g., "venv", "conda", "poetry")
        - location: Path to the environment
        - uv_python: UV_PYTHON value if set
        - uv_cache: UV_CACHE_DIR value if set
        - poetry_active: POETRY_ACTIVE value if set
        - pipenv_active: PIPENV_ACTIVE value if set
        - pdm_project_root: PDM_PROJECT_ROOT value if set
    """
    # Virtualenv/venv
    virtual_env = os.environ.get("VIRTUAL_ENV")
    conda_prefix = os.environ.get("CONDA_PREFIX")
    poetry_active = os.environ.get("POETRY_ACTIVE")
    pipenv_active = os.environ.get("PIPENV_ACTIVE")
    pdm_project_root = os.environ.get("PDM_PROJECT_ROOT")

    # Heuristic: venv active when sys.prefix differs
    is_venv = False
    try:
        is_venv = sys.prefix != getattr(sys, "base_prefix", sys.prefix)
    except Exception:
        is_venv = False

    # uv-related hints (best-effort; uv does not always export markers)
    uv_python = os.environ.get("UV_PYTHON")
    uv_cache = os.environ.get("UV_CACHE_DIR")

    manager: str | None = None
    location: str | None = None

    # Priority order: conda > poetry > pipenv > pdm > venv
    if conda_prefix:
        manager = "conda"
        location = conda_prefix
    elif poetry_active:
        manager = "poetry"
        location = os.environ.get("POETRY_ENV", sys.prefix)
    elif pipenv_active:
        manager = "pipenv"
        location = os.environ.get("PIPENV_VENV_IN_PROJECT", sys.prefix)
    elif pdm_project_root:
        manager = "pdm"
        location = os.environ.get("PDM_PYTHON", sys.prefix)
    elif virtual_env or is_venv:
        manager = "venv"
        location = virtual_env or sys.prefix

    # Flag uv if we see hints
    if uv_python or uv_cache:
        if manager is None:
            manager = "uv"
        else:
            manager = f"{manager}+uv"

    return {
        "manager": manager,
        "location": location,
        "uv_python": uv_python,
        "uv_cache": uv_cache,
        "poetry_active": poetry_active,
        "pipenv_active": pipenv_active,
        "pdm_project_root": pdm_project_root,
    }


def get_directory_tree_json(
    path: str | Path,
    max_depth: int = 2,
    max_items: int = 10,
    current_depth: int = 0,
) -> list[dict[str, Any]]:
    """Generate a JSON representation of directory tree.

    Args:
        path: Path to the directory to traverse.
        max_depth: Maximum depth to traverse.
        max_items: Maximum items per directory level.
        current_depth: Current depth in recursion.

    Returns:
        List of dictionaries representing the directory tree structure.
    """
    if current_depth >= max_depth:
        return [{"type": "ellipsis"}]
    nodes: list[dict[str, Any]] = []
    try:
        items = sorted(Path(path).iterdir(), key=lambda x: (x.is_file(), x.name))
        for item in items[:max_items]:
            node: dict[str, Any] = {
                "name": item.name,
                "type": "file" if item.is_file() else "dir",
            }
            if item.is_dir() and current_depth < max_depth - 1:
                node["children"] = get_directory_tree_json(
                    item, max_depth, max_items, current_depth + 1
                )
            nodes.append(node)
    except PermissionError:
        nodes.append({"type": "permission_denied"})
    return nodes


def get_directory_tree(
    path: str | Path,
    max_depth: int = 2,
    max_items: int = 10,
    current_depth: int = 0,
) -> str:
    """Generate a text representation of directory tree.

    Args:
        path: Path to the directory to traverse.
        max_depth: Maximum depth to traverse.
        max_items: Maximum items per directory level.
        current_depth: Current depth in recursion.

    Returns:
        String representation of the directory tree.
    """
    if current_depth >= max_depth:
        return "  " * current_depth + "..."
    tree: list[str] = []
    try:
        items = sorted(Path(path).iterdir(), key=lambda x: (x.is_file(), x.name))
        for i, item in enumerate(items[:max_items]):
            is_last = i == len(items) - 1 or i == max_items - 1
            prefix = "└── " if is_last else "├── "
            tree.append("  " * current_depth + prefix + item.name)
            if item.is_dir() and current_depth < max_depth - 1:
                tree.append(get_directory_tree(item, max_depth, max_items, current_depth + 1))
    except PermissionError:
        tree.append("  " * current_depth + "└── [Permission Denied]")
    return "\n".join(tree)


@dataclass
class Config:
    """Configuration dataclass for CLI options."""

    show_all: bool
    no_paths: bool
    no_python_path: bool
    show_env: bool
    show_fs: bool
    show_tree: bool
    limit: int
    as_json: bool
    as_yaml: bool
    as_toml: bool
    env_groups: tuple[str, ...]
    env_keys: tuple[str, ...]
    path_filter: str | None
    path_exclude: str | None
    tree_depth: int
    tree_max_items: int


def build_json_output(config: Config) -> dict[str, Any]:
    """Build the JSON output structure.

    Args:
        config: Configuration object with all CLI options.

    Returns:
        Dictionary ready for JSON serialization.
    """
    venv_info = detect_virtual_environment()
    data: dict[str, Any] = {
        "location": {"cwd": os.getcwd(), "home": os.path.expanduser("~")},
        "system": {
            "platform": platform.system(),
            "release": platform.release(),
            "python_version": platform.python_version(),
            "python_implementation": platform.python_implementation(),
            "architecture": platform.machine(),
            "executable": sys.executable,
            "environment": venv_info,
        },
    }

    # PATH
    parts = os.environ.get("PATH", "").split(os.pathsep)
    if config.path_filter:
        parts = [p for p in parts if config.path_filter.lower() in p.lower()]
    if config.path_exclude:
        parts = [p for p in parts if config.path_exclude.lower() not in p.lower()]
    data["path"] = {
        "entries": parts[: config.limit],
        "total": len(parts),
        "shown": min(config.limit, len(parts)),
    }

    # Python path
    if config.show_all and not config.no_python_path:
        data["python_path"] = {
            "entries": sys.path[: config.limit],
            "total": len(sys.path),
            "shown": min(config.limit, len(sys.path)),
        }

    # Env keys selection
    if config.show_all or config.show_env or config.env_groups or config.env_keys:
        keys_from_groups: list[str] = []
        for g in config.env_groups:
            keys_from_groups.extend(ENV_GROUPS.get(g, []))
        selected_env_keys = list(
            dict.fromkeys((keys_from_groups + list(config.env_keys)) or ENV_GROUPS["common"])
        )
        env_map: dict[str, str | None] = {k: os.environ.get(k) for k in selected_env_keys}
        data["environment"] = env_map

    # File system
    if config.show_all or config.show_fs:
        try:
            statvfs = os.statvfs(".")
            total = statvfs.f_frsize * statvfs.f_blocks
            free = statvfs.f_frsize * statvfs.f_bavail
            used = total - free
            usage_percent = (used / total) * 100 if total else 0.0
            data["filesystem"] = {
                "total_bytes": total,
                "free_bytes": free,
                "used_bytes": used,
                "usage_percent": round(usage_percent, 1),
            }
        except Exception:
            data["filesystem"] = None

    # Git
    git_info = get_git_info()
    if git_info:
        data["git"] = git_info
    else:
        data["git"] = None

    # Tree
    if config.show_all or config.show_tree:
        data["tree"] = get_directory_tree_json(
            ".", max_depth=config.tree_depth, max_items=config.tree_max_items
        )

    return data


def build_panels(config: Config, venv_info: dict[str, str | None]) -> list[Panel]:
    """Build the list of panels for text output.

    Args:
        config: Configuration object with all CLI options.
        venv_info: Virtual environment information dictionary.

    Returns:
        List of Rich Panel objects to display.
    """
    panels: list[Panel] = []

    # Always useful
    panels.append(section_cwd_home())

    # System with environment info
    sys_info = Text()
    sys_info.append("🖥️ Platform: ", style="bold")
    sys_info.append(f"{platform.system()} {platform.release()}\n", style="cyan")
    sys_info.append("🐍 Python: ", style="bold")
    sys_info.append(
        f"{platform.python_version()} ({platform.python_implementation()})\n",
        style="green",
    )
    sys_info.append("🏗️ Arch: ", style="bold")
    sys_info.append(f"{platform.machine()}\n", style="blue")
    sys_info.append("📦 Executable: ", style="bold")
    sys_info.append(f"{sys.executable}\n", style="magenta")
    # Virtual environment details
    env_manager = venv_info.get("manager")
    env_location = venv_info.get("location")
    if env_manager or env_location:
        sys_info.append("🧪 Environment: ", style="bold")
        details = (
            f"{env_manager or 'unknown'} at {env_location}" if env_location else f"{env_manager}"
        )
        sys_info.append(details + "\n", style="yellow")
    panels.append(Panel(sys_info, title="System", border_style="cyan", padding=(1, 2)))

    # PATH sections
    if config.show_all or not config.no_paths:
        panels.append(
            section_paths(
                limit=config.limit,
                path_filter=config.path_filter,
                path_exclude=config.path_exclude,
            )
        )
    if config.show_all and not config.no_python_path:
        panels.append(section_python_path(limit=config.limit))

    # Optional sections
    if config.show_all or config.show_env or config.env_groups or config.env_keys:
        keys_from_groups: list[str] = []
        for g in config.env_groups:
            keys_from_groups.extend(ENV_GROUPS.get(g, []))
        selected_keys = list(
            dict.fromkeys((keys_from_groups + list(config.env_keys)) or ENV_GROUPS["common"])
        )
        panels.append(section_env(keys=selected_keys))
    if config.show_all or config.show_fs:
        panels.append(section_fs())
    git_panel = section_git()
    if git_panel is not None:
        panels.append(git_panel)

    return panels


@click.command(context_settings={"help_option_names": ["-h", "--help"]})
@click.version_option(version=__version__, prog_name="pathetic")
@click.option("--all", "show_all", is_flag=True, help="Show all sections")
@click.option("--no-paths", is_flag=True, help="Hide PATH section")
@click.option("--no-python-path", is_flag=True, help="Hide sys.path section")
@click.option("--env", "show_env", is_flag=True, help="Show selected environment variables")
@click.option("--fs", "show_fs", is_flag=True, help="Show file system stats")
@click.option("--tree", "show_tree", is_flag=True, help="Show a small directory tree")
@click.option(
    "--limit",
    type=int,
    default=10,
    show_default=True,
    help="Max rows for PATH and sys.path",
)
@click.option("--json", "as_json", is_flag=True, help="Output as JSON (machine-readable)")
@click.option("--yaml", "as_yaml", is_flag=True, help="Output as YAML (requires pyyaml)")
@click.option("--toml", "as_toml", is_flag=True, help="Output as TOML (requires tomli)")
@click.option(
    "--env-group",
    "env_groups",
    multiple=True,
    type=click.Choice(sorted(ENV_GROUPS.keys())),
    help="Predefined env var groups (repeatable)",
)
@click.option(
    "--env-key",
    "env_keys",
    multiple=True,
    help="Additional environment variable keys (repeatable)",
)
@click.option(
    "--path-filter",
    "path_filter",
    type=str,
    help="Filter PATH entries containing this text (case-insensitive)",
)
@click.option(
    "--path-exclude",
    "path_exclude",
    type=str,
    help="Exclude PATH entries containing this text (case-insensitive)",
)
@click.option(
    "--tree-depth",
    type=int,
    default=2,
    show_default=True,
    help="Maximum depth for directory tree",
)
@click.option(
    "--tree-max-items",
    type=int,
    default=10,
    show_default=True,
    help="Maximum items per directory level in tree",
)
def main(
    show_all: bool,
    no_paths: bool,
    no_python_path: bool,
    show_env: bool,
    show_fs: bool,
    show_tree: bool,
    limit: int,
    as_json: bool,
    as_yaml: bool,
    as_toml: bool,
    env_groups: tuple[str, ...],
    env_keys: tuple[str, ...],
    path_filter: str | None,
    path_exclude: str | None,
    tree_depth: int,
    tree_max_items: int,
) -> None:
    """Display useful system and Python environment info.

    Defaults show: Location, System, PATH summary, Git (if present).
    Use --all for everything; toggle sections with flags.
    """
    console = Console()

    # Validate export format options
    export_formats = sum([as_json, as_yaml, as_toml])
    if export_formats > 1:
        console.print("[red]Error: Only one export format can be specified at a time[/red]")
        sys.exit(1)

    if as_yaml and yaml is None:
        console.print(
            "[red]Error: YAML export requires pyyaml. Install with: uv pip install pyyaml[/red]"
        )
        sys.exit(1)

    if as_toml and tomllib is None:
        console.print(
            "[red]Error: TOML export requires tomli. Install with: uv pip install tomli[/red]"
        )
        sys.exit(1)

    config = Config(
        show_all=show_all,
        no_paths=no_paths,
        no_python_path=no_python_path,
        show_env=show_env,
        show_fs=show_fs,
        show_tree=show_tree,
        limit=limit,
        as_json=as_json,
        as_yaml=as_yaml,
        as_toml=as_toml,
        env_groups=env_groups,
        env_keys=env_keys,
        path_filter=path_filter,
        path_exclude=path_exclude,
        tree_depth=tree_depth,
        tree_max_items=tree_max_items,
    )

    # Handle export formats
    if as_json or as_yaml or as_toml:
        data = build_json_output(config)
        if as_json:
            console.print(json.dumps(data, indent=2))
        elif as_yaml:
            console.print(yaml.dump(data, default_flow_style=False, sort_keys=False))
        elif as_toml:
            # TOML export - note: complex nested structures may not convert perfectly
            try:
                import tomli_w

                console.print(tomli_w.dumps(data))
            except ImportError:
                console.print(
                    "[red]Error: TOML export requires tomli-w. Install with: uv pip install tomli-w[/red]"
                )
                sys.exit(1)
        return

    # Text output
    render_header(console)
    venv_info = detect_virtual_environment()
    panels = build_panels(config, venv_info)

    for p in panels:
        console.print(p)

    # Optional small tree at the end
    if show_all or show_tree:
        tree_text = (
            f"[bold]Directory Tree (max depth {tree_depth}):[/bold]\n"
            f"[dim]{get_directory_tree('.', max_depth=tree_depth, max_items=tree_max_items)}[/dim]"
        )
        console.print(
            Panel(
                tree_text,
                title="Current Directory Structure",
                border_style="yellow",
                padding=(1, 2),
            )
        )


if __name__ == "__main__":
    main()
