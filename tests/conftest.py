"""Pytest configuration and fixtures."""

from unittest.mock import patch

import pytest


@pytest.fixture
def mock_env(monkeypatch):
    """Fixture to provide a clean environment for testing."""
    test_env = {
        "PATH": "/usr/bin:/usr/local/bin:/home/user/bin",
        "HOME": "/home/user",
        "USER": "testuser",
        "SHELL": "/bin/bash",
    }
    for key, value in test_env.items():
        monkeypatch.setenv(key, value)
    return test_env


@pytest.fixture
def mock_git_repo(monkeypatch):
    """Fixture to mock git repository information."""

    def mock_check_output(cmd, **kwargs):
        if "branch" in cmd:
            return b"main\n"
        elif "rev-parse" in cmd:
            return b"abc1234\n"
        elif "status" in cmd:
            return b" M file1.py\n?? file2.txt\n"
        return b""

    with patch("subprocess.check_output", side_effect=mock_check_output):
        yield
