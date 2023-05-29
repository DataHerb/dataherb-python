from pathlib import Path
from dataherb.cmd.sync_git import is_git_repo
import pytest


@pytest.mark.parametrize("path, expected", [pytest.param(Path("."), False)])
def test_is_git_repo(path, expected):
    assert is_git_repo(path), expected
