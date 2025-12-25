"""Test hub manager checkout revision functionality."""

import subprocess
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from interaxions.hub.hub_manager import HubManager


class TestCheckoutRevision:
    """Test _checkout_revision method."""

    def test_checkout_revision_uses_popen_correctly(self):
        """Test that _checkout_revision uses subprocess.Popen correctly for git archive piping."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)

            # Create a fake git repo directory
            repo_path = tmpdir / "test-repo"
            repo_path.mkdir()

            # Create cache directory
            cache_dir = tmpdir / "cache"
            hub = HubManager(cache_dir=cache_dir)

            target_dir = tmpdir / "checkout"

            # Mock subprocess.run for git rev-parse
            mock_run_result = MagicMock()
            mock_run_result.stdout = "abc123def456\n"

            # Mock subprocess.Popen for git archive and tar
            mock_archive_process = MagicMock()
            mock_archive_process.stdout = MagicMock()
            mock_archive_process.returncode = 0

            mock_tar_process = MagicMock()
            mock_tar_process.returncode = 0
            mock_tar_process.communicate.return_value = (b"", b"")

            # Mock the .git directory check
            def mock_exists(self):
                return str(self).endswith(".git")

            with patch("subprocess.run", return_value=mock_run_result) as mock_run, \
                 patch("subprocess.Popen") as mock_popen, \
                 patch.object(Path, "exists", mock_exists):

                # Configure mock_popen to return different processes for each call
                mock_popen.side_effect = [mock_archive_process, mock_tar_process]

                # Execute the method
                hub._checkout_revision(repo_path, "main", target_dir)

                # Verify git rev-parse was called
                mock_run.assert_called_once_with(
                    ["git", "rev-parse", "main"],
                    cwd=repo_path,
                    capture_output=True,
                    text=True,
                    check=True,
                )

                # Verify subprocess.Popen was called twice (git archive and tar)
                assert mock_popen.call_count == 2

                # Check git archive call
                archive_call = mock_popen.call_args_list[0]
                assert archive_call[0][0] == ["git", "archive", "abc123def456"]
                assert archive_call[1]["cwd"] == repo_path
                assert archive_call[1]["stdout"] == subprocess.PIPE

                # Check tar call
                tar_call = mock_popen.call_args_list[1]
                assert tar_call[0][0] == ["tar", "-x", "-C", str(target_dir)]
                assert tar_call[1]["stdin"] == mock_archive_process.stdout
                assert tar_call[1]["stdout"] == subprocess.PIPE
                assert tar_call[1]["stderr"] == subprocess.PIPE

                # Verify archive stdout was closed
                mock_archive_process.stdout.close.assert_called_once()

                # Verify tar process communicate was called
                mock_tar_process.communicate.assert_called_once()

    def test_checkout_revision_no_shell_usage(self):
        """Verify that shell=True is NOT used (fixing the original bug)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)

            repo_path = tmpdir / "test-repo"
            repo_path.mkdir()

            cache_dir = tmpdir / "cache"
            hub = HubManager(cache_dir=cache_dir)

            target_dir = tmpdir / "checkout"

            mock_run_result = MagicMock()
            mock_run_result.stdout = "abc123def456\n"

            mock_archive_process = MagicMock()
            mock_archive_process.stdout = MagicMock()
            mock_archive_process.returncode = 0

            mock_tar_process = MagicMock()
            mock_tar_process.returncode = 0
            mock_tar_process.communicate.return_value = (b"", b"")

            # Mock the .git directory check
            def mock_exists(self):
                return str(self).endswith(".git")

            with patch("subprocess.run", return_value=mock_run_result), \
                 patch("subprocess.Popen") as mock_popen, \
                 patch.object(Path, "exists", mock_exists):

                mock_popen.side_effect = [mock_archive_process, mock_tar_process]

                hub._checkout_revision(repo_path, "main", target_dir)

                # Verify that shell=True was NOT used in any Popen call
                for call_args in mock_popen.call_args_list:
                    kwargs = call_args[1]
                    assert "shell" not in kwargs or kwargs["shell"] is False

                    # Verify that the command is a list, not a string
                    command = call_args[0][0]
                    assert isinstance(command, list)

                    # Verify that pipe character is NOT in the command arguments
                    assert "|" not in command

    def test_checkout_revision_handles_git_archive_error(self):
        """Test error handling when git archive fails."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)

            repo_path = tmpdir / "test-repo"
            repo_path.mkdir()

            cache_dir = tmpdir / "cache"
            hub = HubManager(cache_dir=cache_dir)

            target_dir = tmpdir / "checkout"

            mock_run_result = MagicMock()
            mock_run_result.stdout = "abc123def456\n"

            # Mock git archive to fail
            mock_archive_process = MagicMock()
            mock_archive_process.stdout = MagicMock()
            mock_archive_process.returncode = 128  # Git error code

            mock_tar_process = MagicMock()
            mock_tar_process.returncode = 0
            mock_tar_process.communicate.return_value = (b"", b"")

            # Mock the .git directory check
            def mock_exists(self):
                return str(self).endswith(".git")

            with patch("subprocess.run", return_value=mock_run_result), \
                 patch("subprocess.Popen") as mock_popen, \
                 patch.object(Path, "exists", mock_exists):

                mock_popen.side_effect = [mock_archive_process, mock_tar_process]

                # Should raise RuntimeError
                with pytest.raises(RuntimeError) as exc_info:
                    hub._checkout_revision(repo_path, "main", target_dir)

                assert "Failed to checkout revision" in str(exc_info.value)

    def test_checkout_revision_handles_tar_error(self):
        """Test error handling when tar extraction fails."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)

            repo_path = tmpdir / "test-repo"
            repo_path.mkdir()

            cache_dir = tmpdir / "cache"
            hub = HubManager(cache_dir=cache_dir)

            target_dir = tmpdir / "checkout"

            mock_run_result = MagicMock()
            mock_run_result.stdout = "abc123def456\n"

            mock_archive_process = MagicMock()
            mock_archive_process.stdout = MagicMock()
            mock_archive_process.returncode = 0

            # Mock tar to fail
            mock_tar_process = MagicMock()
            mock_tar_process.returncode = 1
            mock_tar_process.communicate.return_value = (b"", b"tar: Error extracting")

            # Mock the .git directory check
            def mock_exists(self):
                return str(self).endswith(".git")

            with patch("subprocess.run", return_value=mock_run_result), \
                 patch("subprocess.Popen") as mock_popen, \
                 patch.object(Path, "exists", mock_exists):

                mock_popen.side_effect = [mock_archive_process, mock_tar_process]

                # Should raise RuntimeError
                with pytest.raises(RuntimeError) as exc_info:
                    hub._checkout_revision(repo_path, "main", target_dir)

                assert "Failed to checkout revision" in str(exc_info.value)

    def test_checkout_revision_non_git_directory(self):
        """Test that non-git directories are handled by copying."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)

            # Create a non-git directory with a test file
            repo_path = tmpdir / "test-dir"
            repo_path.mkdir()
            test_file = repo_path / "test.txt"
            test_file.write_text("test content")

            cache_dir = tmpdir / "cache"
            hub = HubManager(cache_dir=cache_dir)

            target_dir = tmpdir / "checkout"

            # Should not call git commands for non-git directories
            with patch("subprocess.run") as mock_run, \
                 patch("subprocess.Popen") as mock_popen:

                hub._checkout_revision(repo_path, "main", target_dir)

                # Verify no subprocess calls were made
                mock_run.assert_not_called()
                mock_popen.assert_not_called()

                # Verify the file was copied
                assert (target_dir / "test.txt").exists()
                assert (target_dir / "test.txt").read_text() == "test content"
