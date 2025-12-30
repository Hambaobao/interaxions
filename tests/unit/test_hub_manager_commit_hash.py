"""Test hub manager commit hash resolution functionality."""

import subprocess
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from interaxions.hub.hub_manager import HubManager


class TestGetLocalCommitHash:
    """Test _get_local_commit_hash method."""

    def test_get_local_commit_hash_success(self):
        """Test that _get_local_commit_hash returns correct commit hash."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)

            # Create a fake git repo directory
            repo_path = tmpdir / "test-repo"
            repo_path.mkdir()

            # Create cache directory
            cache_dir = tmpdir / "cache"
            hub = HubManager(cache_dir=cache_dir)

            # Mock subprocess.run for git rev-parse
            mock_result = MagicMock()
            mock_result.stdout = "abc12345\n"

            # Mock the .git directory check
            def mock_exists(self):
                return str(self).endswith(".git")

            with patch("subprocess.run", return_value=mock_result) as mock_run, \
                 patch.object(Path, "exists", mock_exists):

                # Execute the method
                commit_hash = hub._get_local_commit_hash(repo_path)

                # Verify correct commit hash returned
                assert commit_hash == "abc12345"

                # Verify git rev-parse was called correctly
                mock_run.assert_called_once_with(
                    ["git", "rev-parse", "--short=8", "HEAD"],
                    cwd=repo_path,
                    capture_output=True,
                    text=True,
                    check=True,
                )

    def test_get_local_commit_hash_non_git_repo(self):
        """Test that non-git directories return 'HEAD' as fallback."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)

            # Create a non-git directory
            repo_path = tmpdir / "test-dir"
            repo_path.mkdir()

            cache_dir = tmpdir / "cache"
            hub = HubManager(cache_dir=cache_dir)

            # Execute the method (no .git directory exists)
            commit_hash = hub._get_local_commit_hash(repo_path)

            # Should return 'HEAD' as fallback
            assert commit_hash == "HEAD"

    def test_get_local_commit_hash_git_error(self):
        """Test error handling when git command fails."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)

            repo_path = tmpdir / "test-repo"
            repo_path.mkdir()

            cache_dir = tmpdir / "cache"
            hub = HubManager(cache_dir=cache_dir)

            # Mock the .git directory check
            def mock_exists(self):
                return str(self).endswith(".git")

            # Mock subprocess.run to raise CalledProcessError
            error = subprocess.CalledProcessError(128, ["git", "rev-parse"], stderr="fatal error")
            with patch("subprocess.run", side_effect=error), \
                 patch.object(Path, "exists", mock_exists):

                # Should return 'HEAD' as fallback on error
                commit_hash = hub._get_local_commit_hash(repo_path)
                assert commit_hash == "HEAD"
