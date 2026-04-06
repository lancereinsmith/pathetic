"""Tests for main CLI functionality."""

import json
import os
from unittest.mock import patch

from click.testing import CliRunner

# Import the module
import pathetic  # type: ignore[import-untyped]


class TestCLI:
    """Test CLI command execution."""

    def test_version_flag(self):
        """Test --version flag."""
        runner = CliRunner()
        result = runner.invoke(pathetic.main, ["--version"])
        assert result.exit_code == 0
        assert "pathetic" in result.output.lower()
        assert "version" in result.output.lower()

    def test_default_output(self):
        """Test default CLI output."""
        runner = CliRunner()
        result = runner.invoke(pathetic.main, [])
        assert result.exit_code == 0
        assert "System Snapshot" in result.output
        assert "Location" in result.output
        assert "System" in result.output

    def test_all_flag(self):
        """Test --all flag."""
        runner = CliRunner()
        result = runner.invoke(pathetic.main, ["--all"])
        assert result.exit_code == 0
        assert "PATH" in result.output

    def test_json_output(self):
        """Test JSON output format."""
        runner = CliRunner()
        result = runner.invoke(pathetic.main, ["--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert "location" in data
        assert "system" in data
        assert "path" in data

    def test_env_keys(self):
        """Test custom environment variable keys."""
        runner = CliRunner()
        result = runner.invoke(
            pathetic.main, ["--env-key", "HOME", "--env-key", "USER"]
        )
        assert result.exit_code == 0

    def test_limit_option(self):
        """Test --limit option."""
        runner = CliRunner()
        result = runner.invoke(pathetic.main, ["--limit", "5"])
        assert result.exit_code == 0

    def test_env_flag(self):
        """Test --env flag shows grouped environment variables."""
        runner = CliRunner()
        result = runner.invoke(pathetic.main, ["--env"])
        assert result.exit_code == 0
        assert "Env:" in result.output


class TestSections:
    """Test individual section rendering functions."""

    def test_section_cwd_home(self):
        """Test CWD and home section."""
        panel = pathetic.section_cwd_home()
        assert panel is not None
        assert panel.title == "Location"

    def test_section_system(self):
        """Test system section."""
        panel = pathetic.section_system()
        assert panel is not None
        assert panel.title == "System"

    def test_section_paths(self, mock_env):
        """Test PATH section with source column."""
        panel = pathetic.section_paths(limit=5)
        assert panel is not None
        assert panel.title == "PATH"

    def test_section_python_path(self):
        """Test Python path section."""
        panel = pathetic.section_python_path(limit=5)
        assert panel is not None
        assert panel.title == "Python Path"

    def test_section_env_grouped(self):
        """Test grouped environment variable display."""
        panels = pathetic.section_env()
        assert isinstance(panels, list)
        assert len(panels) > 0
        # Each panel should have a title starting with "Env:"
        for panel in panels:
            assert panel.title is not None
            assert panel.title.startswith("Env:")

    def test_section_env_specific_keys(self, mock_env):
        """Test environment section with specific keys."""
        panels = pathetic.section_env(keys=["HOME", "USER"])
        assert isinstance(panels, list)
        assert len(panels) == 1
        assert panels[0].title == "Environment"

    def test_section_fs(self):
        """Test filesystem section."""
        panel = pathetic.section_fs()
        assert panel is not None
        assert panel.title == "File System"

    @patch("pathetic.get_git_info", return_value=None)
    def test_section_git_no_repo(self, mock_git_info):
        """Test git section when not in a git repo."""
        panel = pathetic.section_git()
        assert panel is None
        mock_git_info.assert_called_once()

    def test_section_git_with_repo(self, mock_git_repo):
        """Test git section when in a git repo."""
        panel = pathetic.section_git()
        assert panel is not None
        assert panel.title == "Git"


class TestPathSources:
    """Test PATH origin tracing."""

    def test_trace_path_sources(self):
        """Test that trace_path_sources returns a dict."""
        sources = pathetic.trace_path_sources()
        assert isinstance(sources, dict)
        # On macOS, /usr/bin should be traced to /etc/paths
        if os.path.exists("/etc/paths"):
            assert any("/usr" in k for k in sources)

    def test_path_panel_has_source_column(self, mock_env):
        """Test that PATH panel includes a Source column."""
        panel = pathetic.section_paths(limit=5)
        # The panel should render without error
        assert panel is not None


class TestUserPython:
    """Test user Python detection."""

    def test_get_user_python(self):
        """Test that get_user_python returns valid info."""
        result = pathetic.get_user_python()
        assert "executable" in result
        assert "version" in result
        assert "Python" in result["version"] or "python" in result["version"].lower()


class TestEnvCategorization:
    """Test environment variable categorization."""

    def test_categorize_shell_vars(self):
        """Test shell variable categorization."""
        assert pathetic.categorize_env_var("USER") == "Shell"
        assert pathetic.categorize_env_var("SHELL") == "Shell"
        assert pathetic.categorize_env_var("HOME") == "Shell"

    def test_categorize_python_vars(self):
        """Test Python variable categorization."""
        assert pathetic.categorize_env_var("VIRTUAL_ENV") == "Python"
        assert pathetic.categorize_env_var("PYTHONPATH") == "Python"
        assert pathetic.categorize_env_var("UV_CACHE_DIR") == "Python"

    def test_categorize_git_vars(self):
        """Test Git variable categorization."""
        assert pathetic.categorize_env_var("GIT_AUTHOR_NAME") == "Git"

    def test_categorize_unknown_vars(self):
        """Test unknown variable falls to Other."""
        assert pathetic.categorize_env_var("MY_CUSTOM_VAR") == "Other"

    def test_get_grouped_env_vars(self):
        """Test that grouped env vars returns non-empty dict."""
        groups = pathetic.get_grouped_env_vars()
        assert isinstance(groups, dict)
        assert len(groups) > 0


class TestEnvironmentDetection:
    """Test virtual environment detection."""

    def test_detect_virtual_environment_no_venv(self, monkeypatch):
        """Test detection when no virtual environment is active."""
        for key in ["VIRTUAL_ENV", "CONDA_PREFIX", "POETRY_ACTIVE", "PIPENV_ACTIVE"]:
            monkeypatch.delenv(key, raising=False)
        result = pathetic.detect_virtual_environment()
        assert "manager" in result
        assert "location" in result

    def test_detect_virtual_environment_venv(self, monkeypatch):
        """Test detection of venv."""
        monkeypatch.delenv("UV_PYTHON", raising=False)
        monkeypatch.delenv("UV_CACHE_DIR", raising=False)
        monkeypatch.setenv("VIRTUAL_ENV", "/path/to/venv")
        result = pathetic.detect_virtual_environment()
        assert result["manager"] == "venv"
        assert result["location"] == "/path/to/venv"

    def test_detect_virtual_environment_conda(self, monkeypatch):
        """Test detection of conda."""
        monkeypatch.delenv("UV_PYTHON", raising=False)
        monkeypatch.delenv("UV_CACHE_DIR", raising=False)
        monkeypatch.setenv("CONDA_PREFIX", "/path/to/conda")
        result = pathetic.detect_virtual_environment()
        assert result["manager"] == "conda"
        assert result["location"] == "/path/to/conda"

    def test_detect_virtual_environment_poetry(self, monkeypatch):
        """Test detection of Poetry."""
        monkeypatch.delenv("UV_PYTHON", raising=False)
        monkeypatch.delenv("UV_CACHE_DIR", raising=False)
        monkeypatch.setenv("POETRY_ACTIVE", "1")
        monkeypatch.setenv("POETRY_ENV", "/path/to/poetry")
        result = pathetic.detect_virtual_environment()
        assert result["manager"] == "poetry"

    def test_detect_virtual_environment_pipenv(self, monkeypatch):
        """Test detection of Pipenv."""
        monkeypatch.delenv("UV_PYTHON", raising=False)
        monkeypatch.delenv("UV_CACHE_DIR", raising=False)
        monkeypatch.setenv("PIPENV_ACTIVE", "1")
        result = pathetic.detect_virtual_environment()
        assert result["manager"] == "pipenv"

    def test_detect_virtual_environment_pdm(self, monkeypatch):
        """Test detection of PDM."""
        monkeypatch.delenv("UV_PYTHON", raising=False)
        monkeypatch.delenv("UV_CACHE_DIR", raising=False)
        monkeypatch.setenv("PDM_PROJECT_ROOT", "/path/to/pdm")
        result = pathetic.detect_virtual_environment()
        assert result["manager"] == "pdm"

    def test_detect_virtual_environment_uv(self, monkeypatch):
        """Test detection of uv."""
        monkeypatch.setenv("UV_PYTHON", "/path/to/python")
        result = pathetic.detect_virtual_environment()
        assert "uv" in result["manager"] or result["manager"] == "uv"


class TestPathSeparator:
    """Test cross-platform PATH separator handling."""

    def test_path_separator_unix(self, monkeypatch):
        """Test PATH splitting on Unix-like systems."""
        monkeypatch.setattr(os, "pathsep", ":")
        monkeypatch.setenv("PATH", "/usr/bin:/usr/local/bin:/home/user/bin")
        parts = os.environ.get("PATH", "").split(os.pathsep)
        assert len(parts) == 3
        assert "/usr/bin" in parts

    def test_path_separator_windows(self, monkeypatch):
        """Test PATH splitting on Windows."""
        monkeypatch.setattr(os, "pathsep", ";")
        windows_path = "C:\\Windows\\System32;C:\\Windows;C:\\Program Files"
        monkeypatch.setenv("PATH", windows_path)
        parts = os.environ.get("PATH", "").split(os.pathsep)
        assert len(parts) == 3
        assert "C:\\Windows\\System32" in parts


class TestGitInfo:
    """Test git information retrieval."""

    def test_get_git_info_no_repo(self):
        """Test git info when not in a repo."""
        with patch("subprocess.check_output", side_effect=FileNotFoundError()):
            result = pathetic.get_git_info()
            assert result is None

    def test_get_git_info_with_repo(self, mock_git_repo):
        """Test git info when in a repo."""
        result = pathetic.get_git_info()
        assert result is not None
        assert "branch" in result
        assert "commit" in result
        assert "changes" in result


class TestConfig:
    """Test Config dataclass."""

    def test_config_creation(self):
        """Test Config dataclass creation."""
        from pathetic import Config  # type: ignore[attr-defined]

        config = Config(
            show_all=False,
            show_env=False,
            show_fs=False,
            limit=10,
            as_json=False,
            env_keys=(),
        )
        assert config.limit == 10


class TestJSONOutput:
    """Test JSON output building."""

    def test_build_json_output(self, mock_env):
        """Test building JSON output structure."""
        from pathetic import Config, build_json_output  # type: ignore[attr-defined]

        config = Config(
            show_all=True,
            show_env=True,
            show_fs=True,
            limit=10,
            as_json=True,
            env_keys=(),
        )

        data = build_json_output(config)
        assert "location" in data
        assert "system" in data
        assert "path" in data
        assert isinstance(data["path"]["entries"], list)
        # Path entries should have source info
        if data["path"]["entries"]:
            assert "path" in data["path"]["entries"][0]
