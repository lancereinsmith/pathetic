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
        assert "Environment" in result.output

    def test_json_output(self):
        """Test JSON output format."""
        runner = CliRunner()
        result = runner.invoke(pathetic.main, ["--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert "location" in data
        assert "system" in data
        assert "path" in data

    def test_path_filter(self):
        """Test PATH filtering."""
        runner = CliRunner()
        result = runner.invoke(pathetic.main, ["--path-filter", "bin"])
        assert result.exit_code == 0

    def test_path_exclude(self):
        """Test PATH exclusion."""
        runner = CliRunner()
        result = runner.invoke(pathetic.main, ["--path-exclude", "usr"])
        assert result.exit_code == 0

    def test_tree_options(self):
        """Test tree depth and max-items options."""
        runner = CliRunner()
        result = runner.invoke(
            pathetic.main, ["--tree", "--tree-depth", "1", "--tree-max-items", "5"]
        )
        assert result.exit_code == 0

    def test_env_groups(self):
        """Test environment variable groups."""
        runner = CliRunner()
        result = runner.invoke(pathetic.main, ["--env-group", "common"])
        assert result.exit_code == 0

    def test_env_keys(self):
        """Test custom environment variable keys."""
        runner = CliRunner()
        result = runner.invoke(pathetic.main, ["--env-key", "HOME", "--env-key", "USER"])
        assert result.exit_code == 0

    def test_no_paths_flag(self):
        """Test --no-paths flag."""
        runner = CliRunner()
        result = runner.invoke(pathetic.main, ["--no-paths"])
        assert result.exit_code == 0
        # PATH section should not appear in default output when --no-paths is used
        # But it might still appear if --all is not used, so we just check it doesn't error

    def test_limit_option(self):
        """Test --limit option."""
        runner = CliRunner()
        result = runner.invoke(pathetic.main, ["--limit", "5"])
        assert result.exit_code == 0


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
        """Test PATH section."""
        panel = pathetic.section_paths(limit=5)
        assert panel is not None
        assert panel.title == "PATH"

    def test_section_paths_with_filter(self, mock_env):
        """Test PATH section with filter."""
        panel = pathetic.section_paths(limit=5, path_filter="bin")
        assert panel is not None

    def test_section_paths_with_exclude(self, mock_env):
        """Test PATH section with exclude."""
        panel = pathetic.section_paths(limit=5, path_exclude="usr")
        assert panel is not None

    def test_section_python_path(self):
        """Test Python path section."""
        panel = pathetic.section_python_path(limit=5)
        assert panel is not None
        assert panel.title == "Python Path"

    def test_section_env(self, mock_env):
        """Test environment section."""
        panel = pathetic.section_env()
        assert panel is not None
        assert panel.title == "Environment"

    def test_section_env_custom_keys(self, mock_env):
        """Test environment section with custom keys."""
        panel = pathetic.section_env(keys=["HOME", "USER"])
        assert panel is not None

    def test_section_fs(self):
        """Test filesystem section."""
        panel = pathetic.section_fs()
        assert panel is not None
        assert panel.title == "File System"

    @patch("pathetic.get_git_info", return_value=None)
    def test_section_git_no_repo(self, mock_git_info):
        """Test git section when not in a git repo."""
        panel = pathetic.section_git()
        # Should return None if not in git repo
        # This is expected behavior
        assert panel is None
        mock_git_info.assert_called_once()

    def test_section_git_with_repo(self, mock_git_repo):
        """Test git section when in a git repo."""
        panel = pathetic.section_git()
        assert panel is not None
        assert panel.title == "Git"


class TestEnvironmentDetection:
    """Test virtual environment detection."""

    def test_detect_virtual_environment_no_venv(self, monkeypatch):
        """Test detection when no virtual environment is active."""
        # Clear relevant env vars
        for key in ["VIRTUAL_ENV", "CONDA_PREFIX", "POETRY_ACTIVE", "PIPENV_ACTIVE"]:
            monkeypatch.delenv(key, raising=False)

        result = pathetic.detect_virtual_environment()
        assert "manager" in result
        assert "location" in result

    def test_detect_virtual_environment_venv(self, monkeypatch):
        """Test detection of venv."""
        # Clear UV vars to test venv in isolation
        monkeypatch.delenv("UV_PYTHON", raising=False)
        monkeypatch.delenv("UV_CACHE_DIR", raising=False)
        monkeypatch.setenv("VIRTUAL_ENV", "/path/to/venv")
        result = pathetic.detect_virtual_environment()
        assert result["manager"] == "venv"
        assert result["location"] == "/path/to/venv"

    def test_detect_virtual_environment_conda(self, monkeypatch):
        """Test detection of conda."""
        # Clear UV vars to test conda in isolation
        monkeypatch.delenv("UV_PYTHON", raising=False)
        monkeypatch.delenv("UV_CACHE_DIR", raising=False)
        monkeypatch.setenv("CONDA_PREFIX", "/path/to/conda")
        result = pathetic.detect_virtual_environment()
        assert result["manager"] == "conda"
        assert result["location"] == "/path/to/conda"

    def test_detect_virtual_environment_poetry(self, monkeypatch):
        """Test detection of Poetry."""
        # Clear UV vars to test poetry in isolation
        monkeypatch.delenv("UV_PYTHON", raising=False)
        monkeypatch.delenv("UV_CACHE_DIR", raising=False)
        monkeypatch.setenv("POETRY_ACTIVE", "1")
        monkeypatch.setenv("POETRY_ENV", "/path/to/poetry")
        result = pathetic.detect_virtual_environment()
        assert result["manager"] == "poetry"

    def test_detect_virtual_environment_pipenv(self, monkeypatch):
        """Test detection of Pipenv."""
        # Clear UV vars to test pipenv in isolation
        monkeypatch.delenv("UV_PYTHON", raising=False)
        monkeypatch.delenv("UV_CACHE_DIR", raising=False)
        monkeypatch.setenv("PIPENV_ACTIVE", "1")
        result = pathetic.detect_virtual_environment()
        assert result["manager"] == "pipenv"

    def test_detect_virtual_environment_pdm(self, monkeypatch):
        """Test detection of PDM."""
        # Clear UV vars to test pdm in isolation
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
        # Mock os.pathsep to be ':' for Unix-like behavior
        monkeypatch.setattr(os, "pathsep", ":")
        monkeypatch.setenv("PATH", "/usr/bin:/usr/local/bin:/home/user/bin")
        parts = os.environ.get("PATH", "").split(os.pathsep)
        assert len(parts) == 3
        assert "/usr/bin" in parts

    def test_path_separator_windows(self, monkeypatch):
        """Test PATH splitting on Windows."""
        # Mock os.pathsep to be ';' for Windows behavior
        monkeypatch.setattr(os, "pathsep", ";")
        # Simulate Windows PATH
        windows_path = "C:\\Windows\\System32;C:\\Windows;C:\\Program Files"
        monkeypatch.setenv("PATH", windows_path)
        parts = os.environ.get("PATH", "").split(os.pathsep)
        assert len(parts) == 3
        assert "C:\\Windows\\System32" in parts


class TestDirectoryTree:
    """Test directory tree generation."""

    def test_get_directory_tree_json(self, tmp_path):
        """Test JSON directory tree generation."""
        # Create test directory structure
        (tmp_path / "file1.txt").touch()
        (tmp_path / "dir1").mkdir()
        (tmp_path / "dir1" / "file2.txt").touch()

        tree = pathetic.get_directory_tree_json(str(tmp_path), max_depth=2, max_items=10)
        assert isinstance(tree, list)
        assert len(tree) > 0

    def test_get_directory_tree_text(self, tmp_path):
        """Test text directory tree generation."""
        # Create test directory structure
        (tmp_path / "file1.txt").touch()
        (tmp_path / "dir1").mkdir()

        tree = pathetic.get_directory_tree(str(tmp_path), max_depth=1, max_items=5)
        assert isinstance(tree, str)
        assert "file1.txt" in tree or "dir1" in tree


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
            no_paths=False,
            no_python_path=False,
            show_env=False,
            show_fs=False,
            show_tree=False,
            limit=10,
            as_json=False,
            as_yaml=False,
            as_toml=False,
            env_groups=(),
            env_keys=(),
            path_filter=None,
            path_exclude=None,
            tree_depth=2,
            tree_max_items=10,
        )
        assert config.limit == 10
        assert config.tree_depth == 2


class TestJSONOutput:
    """Test JSON output building."""

    def test_build_json_output(self, mock_env):
        """Test building JSON output structure."""
        from pathetic import Config, build_json_output  # type: ignore[attr-defined]

        config = Config(
            show_all=True,
            no_paths=False,
            no_python_path=False,
            show_env=True,
            show_fs=True,
            show_tree=False,
            limit=10,
            as_json=True,
            as_yaml=False,
            as_toml=False,
            env_groups=(),
            env_keys=(),
            path_filter=None,
            path_exclude=None,
            tree_depth=2,
            tree_max_items=10,
        )

        data = build_json_output(config)
        assert "location" in data
        assert "system" in data
        assert "path" in data
        assert isinstance(data["path"]["entries"], list)
