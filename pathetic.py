#!/usr/bin/env python3
"""A colorful CLI to inspect system, environment, and PATH information."""

import json
import os
import platform
import re
import shutil
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

# Try to import optional dependencies (tomllib for version reading)
try:
    import tomllib  # Python 3.11+
except ImportError:
    try:
        import tomli as tomllib  # type: ignore[no-redef]
    except ImportError:
        tomllib = None  # type: ignore[assignment]


# Version from pyproject.toml (single source of truth)
def _get_version() -> str:
    """Read version from pyproject.toml."""
    try:
        import importlib.metadata

        return importlib.metadata.version("pathetic-cli")
    except Exception:
        try:
            pyproject_path = Path(__file__).parent / "pyproject.toml"
            if pyproject_path.exists():
                if tomllib:
                    with open(pyproject_path, "rb") as f:
                        data = tomllib.load(f)
                        version: str = str(data.get("project", {}).get("version", ""))
                        return version
                else:
                    import re as _re

                    content = pyproject_path.read_text()
                    match = _re.search(r'version\s*=\s*"([^"]+)"', content)
                    if match:
                        return match.group(1)
        except Exception:
            pass
    return "0.0.0"


__version__ = _get_version()


# ---------------------------------------------------------------------------
# Python environment detection (user's active Python, not this tool's)
# ---------------------------------------------------------------------------


def get_user_python() -> dict[str, str]:
    """Find the user's active Python on PATH, not this tool's isolated env."""
    tool_prefix = sys.prefix
    path_dirs = os.environ.get("PATH", "").split(os.pathsep)

    for d in path_dirs:
        # Skip directories inside this tool's own venv
        if d.startswith(tool_prefix):
            continue
        for name in ("python3", "python"):
            candidate = os.path.join(d, name)
            if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
                try:
                    ver = subprocess.check_output(
                        [candidate, "--version"],
                        text=True,
                        timeout=5,
                        stderr=subprocess.STDOUT,
                    ).strip()
                    return {"executable": candidate, "version": ver}
                except Exception:
                    continue

    # Fallback: use shutil.which (might find our own)
    which = shutil.which("python3") or shutil.which("python")
    if which:
        try:
            ver = subprocess.check_output(
                [which, "--version"], text=True, timeout=5, stderr=subprocess.STDOUT
            ).strip()
            return {"executable": which, "version": ver}
        except Exception:
            pass

    return {
        "executable": sys.executable,
        "version": f"Python {platform.python_version()}",
    }


# ---------------------------------------------------------------------------
# PATH origin tracing
# ---------------------------------------------------------------------------

_SHELL_CONFIG_FILES = [
    "~/.zshenv",
    "~/.zprofile",
    "~/.zshrc",
    "~/.zlogin",
    "~/.bash_profile",
    "~/.bashrc",
    "~/.profile",
    "/etc/profile",
    "/etc/zshrc",
    "/etc/zprofile",
]


def trace_path_sources() -> dict[str, str]:
    """Map PATH entries to their likely source file.

    Checks /etc/paths, /etc/paths.d/*, and common shell config files
    for lines that add each path.
    """
    sources: dict[str, str] = {}

    # 1. /etc/paths — base system paths (macOS)
    etc_paths = Path("/etc/paths")
    if etc_paths.exists():
        try:
            for line in etc_paths.read_text().splitlines():
                line = line.strip()
                if line:
                    sources[line] = "/etc/paths"
        except OSError:
            pass

    # 2. /etc/paths.d/* — additional system paths (macOS)
    etc_paths_d = Path("/etc/paths.d")
    if etc_paths_d.is_dir():
        try:
            for f in sorted(etc_paths_d.iterdir()):
                if f.is_file():
                    try:
                        for line in f.read_text().splitlines():
                            line = line.strip()
                            if line:
                                sources[line] = f"/etc/paths.d/{f.name}"
                    except OSError:
                        pass
        except OSError:
            pass

    # 3. Shell config files — look for PATH modifications
    path_pattern = re.compile(
        r"""(?:export\s+)?PATH\s*=|path\s*\+=|PATH\s*:=""",
        re.IGNORECASE,
    )
    home = os.path.expanduser("~")

    # Helper to resolve shell variables in a path string
    def _expand(p: str) -> str:
        return (
            p.replace("$HOME", home)
            .replace("${HOME}", home)
            .replace("~", home)
            .rstrip("/")
        )

    for config_file in _SHELL_CONFIG_FILES:
        expanded = os.path.expanduser(config_file)
        if not os.path.isfile(expanded):
            continue
        try:
            content = Path(expanded).read_text()
        except OSError:
            continue

        display_name = config_file if config_file.startswith("~") else config_file

        for line in content.splitlines():
            stripped = line.strip()
            if stripped.startswith("#") or not stripped:
                continue

            # Check for well-known eval/source that add paths indirectly
            if "brew shellenv" in stripped:
                for hp in ["/opt/homebrew/bin", "/opt/homebrew/sbin"]:
                    if hp not in sources:
                        sources[hp] = f"{display_name} (brew)"
                continue
            if "orbstack" in stripped.lower() and (
                "source" in stripped or stripped.startswith(".")
            ):
                orbstack_bin = os.path.expanduser("~/.orbstack/bin")
                if os.path.isdir(orbstack_bin) and orbstack_bin not in sources:
                    sources[orbstack_bin] = f"{display_name} (orbstack)"
                continue

            # Follow sourced files that commonly modify PATH (e.g. . "$HOME/.cargo/env")
            source_match = re.match(
                r'^(?:source|\.) +["\']?([^\s"\']+)["\']?', stripped
            )
            if source_match:
                sourced_path = _expand(source_match.group(1))
                if os.path.isfile(sourced_path):
                    try:
                        sourced_content = Path(sourced_path).read_text()
                    except OSError:
                        continue
                    # Look for PATH modifications inside the sourced file
                    for sline in sourced_content.splitlines():
                        sline = sline.strip()
                        if sline.startswith("#") or not sline:
                            continue
                        if not path_pattern.search(sline):
                            continue
                        for m in re.finditer(
                            r'(?:\$HOME|\$\{HOME\}|~)?(/[^\s:;"\'`]+)', sline
                        ):
                            raw = m.group(0)
                            if raw in ("$PATH", "${PATH}"):
                                continue
                            resolved = _expand(raw)
                            if resolved and resolved not in sources:
                                # Show as: config_file (sourced_filename)
                                sourced_name = Path(sourced_path).name
                                sources[resolved] = f"{display_name} ({sourced_name})"
                continue

            # Check if this line modifies PATH
            if not path_pattern.search(stripped):
                continue

            # Extract path segments from the line.
            # Match both literal paths (/foo/bar) and variable paths ($HOME/foo, ${HOME}/foo, ~/foo)
            for match in re.finditer(
                r'(?:\$HOME|\$\{HOME\}|~)?(/[^\s:;"\'`]+)', stripped
            ):
                raw = match.group(0)
                # Skip $PATH itself (the variable reference, not a real directory)
                if raw in ("$PATH", "${PATH}"):
                    continue
                resolved = _expand(raw)
                if resolved and resolved not in sources:
                    sources[resolved] = display_name

    # 4. Well-known runtime sources (not from config files)
    for p in os.environ.get("PATH", "").split(os.pathsep):
        if p in sources:
            continue
        # Virtual environment activation
        if "/.venv/" in p or "/venv/" in p:
            sources[p] = "venv activate"
        # VS Code injected paths
        elif "Code/User/globalStorage" in p or "vscode" in p.lower():
            sources[p] = "VS Code"
        # iTerm2 utilities
        elif "iTerm" in p or "iterm" in p.lower():
            sources[p] = "iTerm.app"

    return sources


# ---------------------------------------------------------------------------
# Environment variable categorization
# ---------------------------------------------------------------------------

# Exact-match categories
_ENV_EXACT: dict[str, str] = {
    "USER": "Shell",
    "SHELL": "Shell",
    "TERM": "Shell",
    "LANG": "Shell",
    "HOME": "Shell",
    "LOGNAME": "Shell",
    "PWD": "Shell",
    "OLDPWD": "Shell",
    "TMPDIR": "Shell",
    "SHLVL": "Shell",
    "_": "Shell",
    "EDITOR": "Editor",
    "VISUAL": "Editor",
    "GIT_EDITOR": "Editor",
    "CI": "CI/CD",
    "VIRTUAL_ENV": "Python",
    "CONDA_DEFAULT_ENV": "Python",
}

# Prefix-match categories (checked in order)
_ENV_PREFIXES: list[tuple[str, str]] = [
    ("PYTHON", "Python"),
    ("VIRTUAL_ENV", "Python"),
    ("CONDA_", "Python"),
    ("PIP", "Python"),
    ("UV_", "Python"),
    ("PIPX_", "Python"),
    ("PDM_", "Python"),
    ("POETRY_", "Python"),
    ("GIT_", "Git"),
    ("AWS_", "Cloud"),
    ("GCP_", "Cloud"),
    ("AZURE_", "Cloud"),
    ("GOOGLE_", "Cloud"),
    ("DOCKER_", "Docker"),
    ("COMPOSE_", "Docker"),
    ("GITHUB_", "CI/CD"),
    ("GITLAB_", "CI/CD"),
    ("BUILDKITE", "CI/CD"),
    ("CIRCLE", "CI/CD"),
    ("TRAVIS", "CI/CD"),
    ("JENKINS_", "CI/CD"),
    ("NODE_", "Node.js"),
    ("NPM_", "Node.js"),
    ("NVM_", "Node.js"),
    ("YARN_", "Node.js"),
    ("ZSH_", "Shell"),
    ("BASH_", "Shell"),
    ("TERM_", "Shell"),
    ("LC_", "Shell"),
    ("XDG_", "Shell"),
    ("SSH_", "SSH"),
    ("GPG_", "Security"),
    ("GNUPG_", "Security"),
    ("HTTP_PROXY", "Proxy"),
    ("HTTPS_PROXY", "Proxy"),
    ("NO_PROXY", "Proxy"),
    ("HOMEBREW_", "Homebrew"),
    ("CARGO_", "Rust"),
    ("RUSTUP_", "Rust"),
    ("GOPATH", "Go"),
    ("GOROOT", "Go"),
    ("JAVA_", "Java"),
    ("MAVEN_", "Java"),
    ("GRADLE_", "Java"),
]


def categorize_env_var(key: str) -> str:
    """Categorize an environment variable by its key."""
    if key in _ENV_EXACT:
        return _ENV_EXACT[key]

    key_upper = key.upper()
    for prefix, category in _ENV_PREFIXES:
        if key_upper.startswith(prefix) or key.startswith(prefix.lower()):
            return category

    # Lowercase proxy variants
    if key in ("http_proxy", "https_proxy", "no_proxy"):
        return "Proxy"

    return "Other"


def get_grouped_env_vars() -> dict[str, dict[str, str]]:
    """Get all environment variables grouped by category."""
    groups: dict[str, dict[str, str]] = {}
    for key, value in sorted(os.environ.items()):
        # Skip PATH (shown separately) and internal vars
        if key == "PATH":
            continue
        category = categorize_env_var(key)
        if category not in groups:
            groups[category] = {}
        groups[category][key] = value
    return groups


# ---------------------------------------------------------------------------
# Section renderers
# ---------------------------------------------------------------------------


def render_header(console: Console) -> None:
    """Render the header for the CLI output."""
    console.print("\n[bold blue]🔎 System Snapshot[/bold blue]\n")


def section_cwd_home() -> Panel:
    """Render a panel showing current working directory and home directory."""
    text = Text()
    text.append("📁 CWD: ", style="bold")
    text.append(f"{os.getcwd()}\n", style="green")
    text.append("🏠 Home: ", style="bold")
    text.append(f"{os.path.expanduser('~')}", style="blue")
    return Panel(text, title="Location", border_style="green", padding=(1, 2))


def section_system(venv_info: dict[str, str | None] | None = None) -> Panel:
    """Render a panel showing system info with the user's active Python."""
    user_py = get_user_python()

    info = Text()
    info.append("🖥️ Platform: ", style="bold")
    info.append(f"{platform.system()} {platform.release()}\n", style="cyan")
    info.append("🐍 Python: ", style="bold")
    info.append(f"{user_py['version']}\n", style="green")
    info.append("🏗️ Arch: ", style="bold")
    info.append(f"{platform.machine()}\n", style="blue")
    info.append("📦 Executable: ", style="bold")
    info.append(f"{user_py['executable']}", style="magenta")
    if venv_info:
        env_manager = venv_info.get("manager")
        env_location = venv_info.get("location")
        if env_manager or env_location:
            info.append("\n🧪 Environment: ", style="bold")
            details = (
                f"{env_manager or 'unknown'} at {env_location}"
                if env_location
                else f"{env_manager}"
            )
            info.append(details, style="yellow")
    return Panel(info, title="System", border_style="cyan", padding=(1, 2))


def _count_executables(directory: str) -> int | None:
    """Count executable files in a directory. Returns None if dir doesn't exist."""
    if not os.path.isdir(directory):
        return None
    count = 0
    try:
        for entry in os.scandir(directory):
            try:
                if entry.is_file() and os.access(entry.path, os.X_OK):
                    count += 1
            except (OSError, PermissionError):
                continue
    except (OSError, PermissionError):
        return None
    return count


def section_paths(limit: int = 10) -> Panel:
    """Render a panel showing PATH entries with their source files and contents."""
    parts = os.environ.get("PATH", "").split(os.pathsep)
    sources = trace_path_sources()

    table = Table(
        title=f"PATH (first {min(limit, len(parts))} of {len(parts)})",
        box=box.ROUNDED,
    )
    table.add_column("#", style="cyan", no_wrap=True)
    table.add_column("Path", style="white")
    table.add_column("Cmds", style="green", no_wrap=True, justify="right")
    table.add_column("Source", style="dim", no_wrap=True)
    for i, p in enumerate(parts[:limit], 1):
        display = p or "[dim]<empty>[/dim]"
        source = sources.get(p, sources.get(p.rstrip("/"), ""))
        count = _count_executables(p) if p else None
        cmds = "[red]missing[/red]" if count is None else str(count)
        table.add_row(str(i), display, cmds, source)
    return Panel(table, title="PATH", border_style="yellow", padding=(1, 1))


def section_python_path(limit: int = 10) -> Panel:
    """Render a panel showing Python sys.path entries."""
    table = Table(
        title=f"sys.path (first {min(limit, len(sys.path))} of {len(sys.path)})",
        box=box.ROUNDED,
    )
    table.add_column("#", style="magenta", no_wrap=True)
    table.add_column("Path", style="white")
    for i, p in enumerate(sys.path[:limit], 1):
        table.add_row(str(i), p)
    return Panel(table, title="Python Path", border_style="green", padding=(1, 1))


# Category display order and colors
_CATEGORY_STYLES: dict[str, str] = {
    "Shell": "green",
    "Python": "yellow",
    "Git": "magenta",
    "Editor": "cyan",
    "Cloud": "blue",
    "Docker": "cyan",
    "CI/CD": "red",
    "Node.js": "green",
    "SSH": "magenta",
    "Security": "red",
    "Proxy": "yellow",
    "Homebrew": "yellow",
    "Rust": "red",
    "Go": "cyan",
    "Java": "red",
    "Other": "white",
}

_CATEGORY_ORDER = [
    "Shell",
    "Python",
    "Git",
    "Editor",
    "Cloud",
    "Docker",
    "CI/CD",
    "Node.js",
    "SSH",
    "Security",
    "Proxy",
    "Homebrew",
    "Rust",
    "Go",
    "Java",
    "Other",
]


def section_env(keys: list[str] | None = None) -> list[Panel]:
    """Render panels showing environment variables, grouped by category.

    If specific keys are provided, shows only those.
    Otherwise shows all env vars grouped intelligently.
    """
    if keys:
        # Show specific keys in a single table
        table = Table(title="Selected Environment", box=box.ROUNDED)
        table.add_column("Variable", style="cyan", no_wrap=True)
        table.add_column("Value", style="white")
        for k in keys:
            v = os.environ.get(k, "[dim]Not set[/dim]")
            sv = str(v)
            if len(sv) > 80:
                sv = sv[:77] + "..."
            table.add_row(k, sv)
        return [Panel(table, title="Environment", border_style="blue", padding=(1, 1))]

    # Show all env vars grouped by category
    groups = get_grouped_env_vars()
    panels: list[Panel] = []

    for category in _CATEGORY_ORDER:
        if category not in groups:
            continue
        env_vars = groups[category]
        style = _CATEGORY_STYLES.get(category, "white")

        table = Table(box=box.SIMPLE_HEAVY, show_header=True, padding=(0, 1))
        table.add_column("Variable", style="cyan", no_wrap=True)
        table.add_column("Value", style="white", overflow="fold")
        for k, v in sorted(env_vars.items()):
            sv = v if len(v) <= 120 else v[:117] + "..."
            table.add_row(k, sv)
        panels.append(
            Panel(table, title=f"Env: {category}", border_style=style, padding=(0, 1))
        )

    return panels


def section_fs() -> Panel:
    """Render a panel showing filesystem statistics."""
    statvfs_fn = getattr(os, "statvfs", None)
    if statvfs_fn is None:
        return Panel("Unavailable", title="File System", border_style="red")
    try:
        statvfs = statvfs_fn(".")
    except OSError:
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
    """Get git information with timeout and better error handling."""
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
    except (
        subprocess.CalledProcessError,
        FileNotFoundError,
        subprocess.TimeoutExpired,
    ):
        return None


def section_git(timeout: float = 5.0) -> Panel | None:
    """Render a panel showing git repository information."""
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
    """Detect and return information about the active Python environment."""
    virtual_env = os.environ.get("VIRTUAL_ENV")
    conda_prefix = os.environ.get("CONDA_PREFIX")
    poetry_active = os.environ.get("POETRY_ACTIVE")
    pipenv_active = os.environ.get("PIPENV_ACTIVE")
    pdm_project_root = os.environ.get("PDM_PROJECT_ROOT")

    is_venv = False
    try:
        is_venv = sys.prefix != getattr(sys, "base_prefix", sys.prefix)
    except Exception:
        is_venv = False

    uv_python = os.environ.get("UV_PYTHON")
    uv_cache = os.environ.get("UV_CACHE_DIR")

    manager: str | None = None
    location: str | None = None

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

    if uv_python or uv_cache:
        manager = "uv" if manager is None else f"{manager}+uv"

    return {
        "manager": manager,
        "location": location,
        "uv_python": uv_python,
        "uv_cache": uv_cache,
        "poetry_active": poetry_active,
        "pipenv_active": pipenv_active,
        "pdm_project_root": pdm_project_root,
    }


# ---------------------------------------------------------------------------
# Config and output builders
# ---------------------------------------------------------------------------


@dataclass
class Config:
    """Configuration dataclass for CLI options."""

    show_all: bool
    show_env: bool
    show_fs: bool
    limit: int
    as_json: bool
    env_keys: tuple[str, ...]


def build_json_output(config: Config) -> dict[str, Any]:
    """Build the JSON output structure."""
    venv_info = detect_virtual_environment()
    user_py = get_user_python()
    data: dict[str, Any] = {
        "location": {"cwd": os.getcwd(), "home": os.path.expanduser("~")},
        "system": {
            "platform": platform.system(),
            "release": platform.release(),
            "python_version": user_py["version"],
            "architecture": platform.machine(),
            "python_executable": user_py["executable"],
            "environment": venv_info,
        },
    }

    # PATH with sources
    parts = os.environ.get("PATH", "").split(os.pathsep)
    sources = trace_path_sources()
    path_entries = []
    for p in parts[: config.limit]:
        entry: dict[str, str] = {"path": p}
        source = sources.get(p, sources.get(p.rstrip("/"), ""))
        if source:
            entry["source"] = source
        path_entries.append(entry)
    data["path"] = {
        "entries": path_entries,
        "total": len(parts),
        "shown": min(config.limit, len(parts)),
    }

    # Python path (with --all)
    if config.show_all:
        data["python_path"] = {
            "entries": sys.path[: config.limit],
            "total": len(sys.path),
            "shown": min(config.limit, len(sys.path)),
        }

    # Environment variables
    if config.show_all or config.show_env or config.env_keys:
        if config.env_keys:
            env_map: dict[str, str | None] = {
                k: os.environ.get(k) for k in config.env_keys
            }
            data["environment"] = env_map
        else:
            data["environment"] = get_grouped_env_vars()

    # File system
    if config.show_all or config.show_fs:
        statvfs_fn = getattr(os, "statvfs", None)
        if statvfs_fn is None:
            data["filesystem"] = None
        else:
            try:
                statvfs = statvfs_fn(".")
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
    data["git"] = git_info

    return data


def render_output(console: Console, config: Config) -> None:
    """Render panels in a responsive columnar layout based on terminal width."""
    render_header(console)
    venv_info = detect_virtual_environment()
    width = console.width

    # Compact panels: small text-based info that fits side-by-side
    compact: list[Panel] = [section_cwd_home(), section_system(venv_info)]
    git_panel = section_git()
    if git_panel is not None:
        compact.append(git_panel)
    if config.show_all or config.show_fs:
        compact.append(section_fs())

    # Determine columns for compact panels based on terminal width
    if width >= 140:
        cols = 3
    elif width >= 90:
        cols = 2
    else:
        cols = 1

    # Lay out compact panels in a grid
    grid = Table.grid(expand=True)
    for _ in range(cols):
        grid.add_column(ratio=1)
    for i in range(0, len(compact), cols):
        row = compact[i : i + cols]
        while len(row) < cols:
            row.append(Text(""))  # type: ignore[arg-type]
        grid.add_row(*row)
    console.print(grid)

    # Wide panels: tables that benefit from full width
    console.print(section_paths(limit=config.limit))
    if config.show_all:
        console.print(section_python_path(limit=config.limit))

    # Environment variables
    if config.show_all or config.show_env or config.env_keys:
        keys = list(config.env_keys) if config.env_keys else None
        env_panels = section_env(keys=keys)
        for p in env_panels:
            console.print(p)


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


@click.command(context_settings={"help_option_names": ["-h", "--help"]})
@click.version_option(version=__version__, prog_name="pathetic")
@click.option("--all", "show_all", is_flag=True, help="Show all sections")
@click.option("--env", "show_env", is_flag=True, help="Show environment variables")
@click.option("--fs", "show_fs", is_flag=True, help="Show file system stats")
@click.option(
    "--limit",
    type=int,
    default=25,
    show_default=True,
    help="Max rows for PATH and sys.path",
)
@click.option(
    "--json", "as_json", is_flag=True, help="Output as JSON (machine-readable)"
)
@click.option(
    "--env-key",
    "env_keys",
    multiple=True,
    help="Show specific env vars (repeatable)",
)
def main(
    show_all: bool,
    show_env: bool,
    show_fs: bool,
    limit: int,
    as_json: bool,
    env_keys: tuple[str, ...],
) -> None:
    """Display useful system and Python environment info.

    Defaults show: Location, System, PATH summary, Git (if present).
    Use --all for everything; toggle sections with flags.
    """
    console = Console()

    config = Config(
        show_all=show_all,
        show_env=show_env,
        show_fs=show_fs,
        limit=limit,
        as_json=as_json,
        env_keys=env_keys,
    )

    if as_json:
        data = build_json_output(config)
        click.echo(json.dumps(data, indent=2))
        return

    render_output(console, config)


if __name__ == "__main__":
    main()
