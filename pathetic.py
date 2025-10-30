#!/usr/bin/env python3
import json
import os
import platform
import subprocess
import sys
from pathlib import Path

import click
from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text


def render_header(console: Console) -> None:
    console.print("\n[bold blue]🔎 System Snapshot[/bold blue]\n")


def section_cwd_home() -> Panel:
    text = Text()
    text.append("📁 CWD: ", style="bold")
    text.append(f"{os.getcwd()}\n", style="green")
    text.append("🏠 Home: ", style="bold")
    text.append(f"{os.path.expanduser('~')}", style="blue")
    return Panel(text, title="Location", border_style="green", padding=(1, 2))


def section_system() -> Panel:
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


def section_paths(limit: int = 10) -> Panel:
    parts = os.environ.get("PATH", "").split(":")
    table = Table(
        title="PATH (first {0} of {1})".format(min(limit, len(parts)), len(parts)),
        box=box.ROUNDED,
    )
    table.add_column("#", style="cyan", no_wrap=True)
    table.add_column("Path", style="white")
    for i, p in enumerate(parts[:limit], 1):
        table.add_row(str(i), p or "[dim]<empty>[/dim]")
    return Panel(table, title="PATH", border_style="yellow", padding=(1, 1))


def section_python_path(limit: int = 10) -> Panel:
    table = Table(
        title="sys.path (first {0} of {1})".format(
            min(limit, len(sys.path)), len(sys.path)
        ),
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
}


def section_env(keys: list[str] | None = None) -> Panel:
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
    try:
        statvfs = os.statvfs(".")
    except (OSError, AttributeError):
        return Panel("Unavailable", title="File System", border_style="red")

    def fmt(b: float) -> str:
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


def section_git() -> Panel | None:
    try:
        branch = subprocess.check_output(
            ["git", "branch", "--show-current"], stderr=subprocess.DEVNULL, text=True
        ).strip()
        commit = subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            stderr=subprocess.DEVNULL,
            text=True,
        ).strip()
        status = subprocess.check_output(
            ["git", "status", "--porcelain"], stderr=subprocess.DEVNULL, text=True
        ).strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None

    info = Text()
    info.append("🌿 Branch: ", style="bold")
    info.append(f"{branch}\n", style="green")
    info.append("📝 Commit: ", style="bold")
    info.append(f"{commit}\n", style="blue")
    info.append("📋 Status: ", style="bold")
    info.append(
        f"{len(status.splitlines())} changes" if status else "Clean", style="yellow"
    )
    return Panel(info, title="Git", border_style="green", padding=(1, 2))


def detect_virtual_environment() -> dict[str, str | None]:
    """Return information about the active Python environment, if any."""
    # Virtualenv/venv
    virtual_env = os.environ.get("VIRTUAL_ENV")
    conda_prefix = os.environ.get("CONDA_PREFIX")

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
    if conda_prefix:
        manager = "conda"
        location = conda_prefix
    elif virtual_env or is_venv:
        manager = "venv"
        location = virtual_env or sys.prefix
    # flag uv if we see hints
    if uv_python or uv_cache:
        manager = "uv" if manager is None else f"{manager}+uv"

    return {
        "manager": manager,
        "location": location,
        "uv_python": uv_python,
        "uv_cache": uv_cache,
    }


@click.command(context_settings={"help_option_names": ["-h", "--help"]})
@click.option("--all", "show_all", is_flag=True, help="Show all sections")
@click.option("--no-paths", is_flag=True, help="Hide PATH section")
@click.option("--no-python-path", is_flag=True, help="Hide sys.path section")
@click.option(
    "--env", "show_env", is_flag=True, help="Show selected environment variables"
)
@click.option("--fs", "show_fs", is_flag=True, help="Show file system stats")
@click.option("--tree", "show_tree", is_flag=True, help="Show a small directory tree")
@click.option(
    "--limit",
    type=int,
    default=10,
    show_default=True,
    help="Max rows for PATH and sys.path",
)
@click.option(
    "--json", "as_json", is_flag=True, help="Output as JSON (machine-readable)"
)
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
def main(
    show_all: bool,
    no_paths: bool,
    no_python_path: bool,
    show_env: bool,
    show_fs: bool,
    show_tree: bool,
    limit: int,
    as_json: bool,
    env_groups: tuple[str, ...],
    env_keys: tuple[str, ...],
) -> None:
    """Display useful system and Python environment info.

    Defaults show: Location, System, PATH summary, Git (if present).
    Use --all for everything; toggle sections with flags.
    """
    console = Console()
    # Build structured data for possible JSON output
    venv_info = detect_virtual_environment()
    data: dict[str, object] = {
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

    if as_json:
        # Fill in optional sections in JSON for parity with text output defaults
        # PATH
        parts = os.environ.get("PATH", "").split(":")
        data["path"] = {
            "entries": parts[:limit],
            "total": len(parts),
            "shown": min(limit, len(parts)),
        }

        # Python path (only when --all in text UI; include in JSON when requested via --all)
        if show_all and not no_python_path:
            data["python_path"] = {
                "entries": sys.path[:limit],
                "total": len(sys.path),
                "shown": min(limit, len(sys.path)),
            }

        # Env keys selection
        selected_env_keys: list[str] | None = None
        if show_all or show_env or env_groups or env_keys:
            keys_from_groups: list[str] = []
            for g in env_groups:
                keys_from_groups.extend(ENV_GROUPS.get(g, []))
            selected_env_keys = list(
                dict.fromkeys(
                    (keys_from_groups + list(env_keys)) or ENV_GROUPS["common"]
                )
            )
            env_map: dict[str, str | None] = {
                k: os.environ.get(k) for k in selected_env_keys
            }
            data["environment"] = env_map

        # File system
        if show_all or show_fs:
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
        try:
            branch = subprocess.check_output(
                ["git", "branch", "--show-current"],
                stderr=subprocess.DEVNULL,
                text=True,
            ).strip()
            commit = subprocess.check_output(
                ["git", "rev-parse", "--short", "HEAD"],
                stderr=subprocess.DEVNULL,
                text=True,
            ).strip()
            status = subprocess.check_output(
                ["git", "status", "--porcelain"], stderr=subprocess.DEVNULL, text=True
            ).strip()
            data["git"] = {
                "branch": branch,
                "short_commit": commit,
                "changes": len(status.splitlines()) if status else 0,
            }
        except Exception:
            data["git"] = None

        # Tree
        if show_all or show_tree:

            def get_directory_tree_json(
                path: str | Path, max_depth: int = 2, current_depth: int = 0
            ) -> list[dict[str, object]]:
                if current_depth >= max_depth:
                    return [{"type": "ellipsis"}]
                nodes: list[dict[str, object]] = []
                try:
                    items = sorted(
                        Path(path).iterdir(), key=lambda x: (x.is_file(), x.name)
                    )
                    for item in items[:10]:
                        node: dict[str, object] = {
                            "name": item.name,
                            "type": "file" if item.is_file() else "dir",
                        }
                        if item.is_dir() and current_depth < max_depth - 1:
                            node["children"] = get_directory_tree_json(
                                item, max_depth, current_depth + 1
                            )
                        nodes.append(node)
                except PermissionError:
                    nodes.append({"type": "permission_denied"})
                return nodes

            data["tree"] = get_directory_tree_json(".")

        # Emit JSON and return
        console.print(json.dumps(data, indent=2))
        return

    render_header(console)

    panels: list[Panel] = []

    # Always useful
    panels.append(section_cwd_home())
    # System with environment info
    # Append environment details into the system panel rendering by creating an augmented Text
    # Rebuild to include venv/conda/uv info prominently
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
            f"{env_manager or 'unknown'} at {env_location}"
            if env_location
            else f"{env_manager}"
        )
        sys_info.append(details + "\n", style="yellow")
    panels.append(Panel(sys_info, title="System", border_style="cyan", padding=(1, 2)))

    # PATH sections
    if show_all or not no_paths:
        panels.append(section_paths(limit=limit))
    if show_all or (not no_python_path and show_all):
        pass  # handled by show_all below
    if show_all and not no_python_path:
        panels.append(section_python_path(limit=limit))

    # Optional sections
    if show_all or show_env or env_groups or env_keys:
        keys_from_groups: list[str] = []
        for g in env_groups:
            keys_from_groups.extend(ENV_GROUPS.get(g, []))
        selected_keys = list(
            dict.fromkeys((keys_from_groups + list(env_keys)) or ENV_GROUPS["common"])
        )
        panels.append(section_env(keys=selected_keys))
    if show_all or show_fs:
        panels.append(section_fs())
    git_panel = section_git()
    if git_panel is not None:
        panels.append(git_panel)

    for p in panels:
        console.print(p)

    # Optional small tree at the end
    if show_all or show_tree:

        def get_directory_tree(
            path: str | Path, max_depth: int = 2, current_depth: int = 0
        ) -> str:
            if current_depth >= max_depth:
                return "  " * current_depth + "..."
            tree: list[str] = []
            try:
                items = sorted(
                    Path(path).iterdir(), key=lambda x: (x.is_file(), x.name)
                )
                for i, item in enumerate(items[:10]):
                    is_last = i == len(items) - 1 or i == 9
                    prefix = "└── " if is_last else "├── "
                    tree.append("  " * current_depth + prefix + item.name)
                    if item.is_dir() and current_depth < max_depth - 1:
                        tree.append(
                            get_directory_tree(item, max_depth, current_depth + 1)
                        )
            except PermissionError:
                tree.append("  " * current_depth + "└── [Permission Denied]")
            return "\n".join(tree)

        tree_text = f"[bold]Directory Tree (max depth 2):[/bold]\n[dim]{get_directory_tree('.')}[/dim]"
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
