"""
Hub manager for dynamic loading and caching of agent/environment modules.

This is similar to transformers' cached_download and file_download utilities,
but specialized for loading Python modules from git repositories.

Environment Variables (similar to HuggingFace Transformers):
    IX_HOME: Base directory for Interaxions data (default: ~/.interaxions)
             Similar to HF_HOME in transformers.
    IX_HUB_CACHE: Hub cache directory (default: $IX_HOME/hub)
                  Similar to TRANSFORMERS_CACHE in transformers.
    
Example:
    export IX_HOME=/data/interaxions
    export IX_HUB_CACHE=/data/interaxions/hub
"""

import sys
import logging
import hashlib
import importlib.util
import shutil
import subprocess
import fcntl
import time
import os

from pathlib import Path
from typing import Optional, Dict, Any, Tuple

from interaxions.hub.constants import get_hub_cache_dir

logger = logging.getLogger(__name__)


class HubManager:
    """
    Manager for loading and caching modules from repositories.
    
    Similar to transformers' snapshot_download() but for Python modules.
    Supports version control (tag, branch, commit) and caching.
    """

    def __init__(self, cache_dir: Optional[Path] = None):
        """
        Initialize the hub manager.
        
        Args:
            cache_dir: Directory for caching downloaded repositories.
                      If None, uses environment variables or default (~/.interaxions/hub).
                      Environment variables:
                        - IX_HUB_CACHE: Direct cache path (highest priority)
                        - IX_HOME: Base directory (cache will be $IX_HOME/hub)
                      
                      Similar to transformers: HF_HOME and TRANSFORMERS_CACHE.
        """
        if cache_dir is None:
            cache_dir = get_hub_cache_dir()

        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # In-memory cache of loaded modules
        # Key: (repo_path, revision, module_name)
        # Value: loaded module object
        self._module_cache: Dict[Tuple[str, str, str], Any] = {}

        logger.info(f"Initialized HubManager with cache_dir: {self.cache_dir}")

    def _get_cache_key(self, repo_path: str, revision: str) -> str:
        """
        Generate cache key for a repository and revision.
        
        Args:
            repo_path: Repository path (e.g., "ix-hub/swe-agent")
            revision: Git revision (tag, branch, or commit hash)
            
        Returns:
            Cache key string.
        """
        # Create a hash-based key
        key_str = f"{repo_path}@{revision}"
        key_hash = hashlib.sha256(key_str.encode()).hexdigest()[:16]
        # Make it human-readable too
        safe_path = repo_path.replace("/", "--")
        return f"{safe_path}--{revision}--{key_hash}"

    def _get_cached_path(self, repo_path: str, revision: str) -> Path:
        """
        Get the local cache path for a repository and revision.
        
        Args:
            repo_path: Repository path (e.g., "ix-hub/swe-agent")
            revision: Git revision (tag, branch, or commit hash)
            
        Returns:
            Local cache directory path.
        """
        cache_key = self._get_cache_key(repo_path, revision)
        return self.cache_dir / cache_key

    def _get_lock_file(self, repo_path: str, revision: str) -> Path:
        """
        Get the lock file path for a repository and revision.
        
        Args:
            repo_path: Repository path
            revision: Git revision
            
        Returns:
            Lock file path.
        """
        cache_key = self._get_cache_key(repo_path, revision)
        return self.cache_dir / f"{cache_key}.lock"

    def _acquire_lock(self, lock_file: Path, timeout: float = 300.0) -> Any:
        """
        Acquire a file lock for atomic operations.
        
        This ensures that only one process can download/clone a repository at a time.
        
        Args:
            lock_file: Path to the lock file
            timeout: Maximum time to wait for lock (seconds)
            
        Returns:
            File handle (must be kept open to maintain lock)
            
        Raises:
            TimeoutError: If lock cannot be acquired within timeout
        """
        lock_file.parent.mkdir(parents=True, exist_ok=True)

        # Open lock file
        lock_fd = open(lock_file, 'w')

        start_time = time.time()
        while True:
            try:
                # Try to acquire exclusive lock (non-blocking)
                fcntl.flock(lock_fd.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                logger.debug(f"Acquired lock: {lock_file}")
                return lock_fd
            except IOError:
                # Lock is held by another process
                elapsed = time.time() - start_time
                if elapsed >= timeout:
                    lock_fd.close()
                    raise TimeoutError(f"Failed to acquire lock within {timeout}s: {lock_file}\n"
                                       f"Another process may be downloading the same repository.")
                # Wait a bit before retrying
                time.sleep(0.1)

    def _release_lock(self, lock_fd: Any) -> None:
        """
        Release a file lock.
        
        Args:
            lock_fd: File handle returned by _acquire_lock
        """
        try:
            fcntl.flock(lock_fd.fileno(), fcntl.LOCK_UN)
            lock_fd.close()
            logger.debug("Released lock")
        except Exception as e:
            logger.warning(f"Error releasing lock: {e}")

    def _resolve_repo_path(self, repo_path: str) -> Path:
        """
        Resolve repository path to absolute path.
        
        Supports:
        - Relative paths (e.g., "ix-hub/swe-agent")
        - Absolute paths (e.g., "/path/to/ix-hub/swe-agent")
        - Remote paths (e.g., "username/repo" -> downloads from IX_ENDPOINT or GitHub)
        
        Args:
            repo_path: Repository path.
            
        Returns:
            Absolute path to the repository.
            
        Raises:
            FileNotFoundError: If repository path doesn't exist.
        """
        path = Path(repo_path)

        # If absolute path, use as-is
        if path.is_absolute():
            if not path.exists():
                raise FileNotFoundError(f"Repository not found: {path}")
            return path

        # Try relative to current working directory
        full_path = Path.cwd() / path
        if full_path.exists():
            return full_path.resolve()

        # Path doesn't exist locally, try remote
        if os.getenv("IX_OFFLINE") == "true":
            raise FileNotFoundError(f"Repository not found: {repo_path}\n"
                                    f"Tried: {full_path}\n"
                                    f"Working directory: {Path.cwd()}\n"
                                    f"Remote download disabled (IX_OFFLINE=true)")

        # Try to download from remote
        logger.info(f"Local path not found, trying remote: {repo_path}")
        return self._clone_remote_repo(repo_path, self._to_git_url(repo_path))

    def _to_git_url(self, repo_path: str) -> str:
        """
        Convert a repository path to a Git URL.
        
        Uses IX_ENDPOINT environment variable if set, otherwise defaults to GitHub.
        
        Args:
            repo_path: Repository path (e.g., "username/repo")
            
        Returns:
            Git URL (e.g., "https://github.com/username/repo.git")
            
        Examples:
            IX_ENDPOINT not set:
                "username/repo" -> "https://github.com/username/repo.git"
            
            IX_ENDPOINT="https://gitlab.com":
                "username/repo" -> "https://gitlab.com/username/repo.git"
        """
        # Check for custom endpoint
        endpoint = os.getenv("IX_ENDPOINT")
        if endpoint:
            # Custom Git service (e.g., GitLab, Gitea, enterprise Git)
            return f"{endpoint.rstrip('/')}/{repo_path}.git"

        # Default to GitHub
        return f"https://github.com/{repo_path}.git"

    def _clone_remote_repo(self, repo_path: str, git_url: str) -> Path:
        """
        Clone a remote Git repository to cache (with file lock protection).
        
        Args:
            repo_path: Repository path (for cache key)
            git_url: Git URL to clone from
            
        Returns:
            Path to the cloned repository
            
        Raises:
            RuntimeError: If git clone fails
        """
        # Use a special cache key for remote repos
        cache_key = hashlib.sha256(git_url.encode()).hexdigest()[:16]
        clone_dir = self.cache_dir / f"remote-{cache_key}"

        # Fast path: check if already cloned (no lock needed)
        if clone_dir.exists():
            logger.info(f"Using cached remote repository: {clone_dir}")
            return clone_dir

        # Need to clone - acquire lock for atomic operation
        lock_file = self.cache_dir / f"remote-{cache_key}.lock"
        lock_fd = None

        try:
            lock_fd = self._acquire_lock(lock_file)

            # Double-check: another process may have cloned while we waited
            if clone_dir.exists():
                logger.info(f"Using cached remote repository (cloned by another process): {clone_dir}")
                return clone_dir

            logger.info(f"Cloning remote repository: {git_url}")
            logger.info(f"This may take a while...")

            # Shallow clone (faster, smaller)
            subprocess.run(
                [
                    "git",
                    "clone",
                    "--depth",
                    "1",  # Shallow clone
                    "--quiet",  # Less verbose
                    git_url,
                    str(clone_dir),
                ],
                check=True,
                capture_output=True,
                text=True,
            )

            logger.info(f"Successfully cloned to: {clone_dir}")
            return clone_dir

        except subprocess.CalledProcessError as e:
            # Clean up on failure
            if clone_dir.exists():
                shutil.rmtree(clone_dir)

            error_msg = e.stderr if e.stderr else str(e)
            raise RuntimeError(f"Failed to clone repository: {git_url}\n"
                               f"Error: {error_msg}\n"
                               f"Hint: Make sure git is installed and you have access to the repository")

        finally:
            # Always release lock
            if lock_fd is not None:
                self._release_lock(lock_fd)
                # Clean up lock file
                try:
                    lock_file.unlink(missing_ok=True)
                except Exception:
                    pass

    def _checkout_revision(self, repo_path: Path, revision: str, target_dir: Path) -> None:
        """
        Checkout a specific revision of a repository to target directory.
        
        Uses git worktree to create an isolated checkout without affecting
        the original repository.
        
        Args:
            repo_path: Path to the git repository.
            revision: Git revision (tag, branch, commit).
            target_dir: Target directory for checkout.
            
        Raises:
            RuntimeError: If git operations fail.
        """
        # Check if it's a git repository
        if not (repo_path / ".git").exists():
            # Not a git repo, just copy the directory
            logger.info(f"Not a git repository, copying directory: {repo_path}")
            shutil.copytree(repo_path, target_dir, dirs_exist_ok=True)
            return

        try:
            # Use git archive to export specific revision
            # This is cleaner than worktree and doesn't modify the source repo
            logger.info(f"Checking out revision '{revision}' from {repo_path}")

            # First, resolve the revision to a commit hash
            result = subprocess.run(
                ["git", "rev-parse", revision],
                cwd=repo_path,
                capture_output=True,
                text=True,
                check=True,
            )
            commit_hash = result.stdout.strip()
            logger.info(f"Resolved '{revision}' to commit {commit_hash}")

            # Create target directory
            target_dir.mkdir(parents=True, exist_ok=True)

            # Use git archive to export the tree
            subprocess.run(
                ["git", "archive", commit_hash, "|", "tar", "-x", "-C", str(target_dir)],
                cwd=repo_path,
                shell=True,
                check=True,
            )

            logger.info(f"Successfully checked out to {target_dir}")

        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Failed to checkout revision '{revision}' from {repo_path}:\n"
                               f"Error: {e.stderr if hasattr(e, 'stderr') else str(e)}")

    def get_module_path(
        self,
        repo_path: str,
        revision: str = "main",
        force_reload: bool = False,
    ) -> Path:
        """
        Get the path to a cached module for a specific revision.
        
        This method is thread-safe and process-safe:
        1. Checks if the revision is already cached
        2. If not, acquires a file lock to ensure atomic download
        3. Double-checks cache after acquiring lock (another process may have downloaded)
        4. Downloads/checks out if still not cached
        5. Returns the cached path
        
        Args:
            repo_path: Repository path (e.g., "ix-hub/swe-agent").
            revision: Git revision (tag, branch, or commit hash).
            force_reload: If True, re-download even if cached.
            
        Returns:
            Path to the cached module directory.
        """
        cached_path = self._get_cached_path(repo_path, revision)

        # Fast path: check if already cached (no lock needed for read)
        if cached_path.exists() and not force_reload:
            logger.info(f"Using cached module: {cached_path}")
            return cached_path

        # Need to download - acquire lock for atomic operation
        lock_file = self._get_lock_file(repo_path, revision)
        lock_fd = None

        try:
            lock_fd = self._acquire_lock(lock_file)

            # Double-check: another process may have downloaded while we waited for lock
            if cached_path.exists() and not force_reload:
                logger.info(f"Using cached module (downloaded by another process): {cached_path}")
                return cached_path

            # Resolve source repository
            source_path = self._resolve_repo_path(repo_path)

            # Clean up existing cache if force_reload
            if cached_path.exists() and force_reload:
                logger.info(f"Force reload: removing cached module {cached_path}")
                shutil.rmtree(cached_path)

            # Checkout revision to cache
            logger.info(f"Caching module {repo_path}@{revision} to {cached_path}")
            self._checkout_revision(source_path, revision, cached_path)

            return cached_path

        finally:
            # Always release lock
            if lock_fd is not None:
                self._release_lock(lock_fd)
                # Clean up lock file
                try:
                    lock_file.unlink(missing_ok=True)
                except Exception:
                    pass

    def load_module(self, repo_path: str, module_name: str, revision: str = "main", force_reload: bool = False) -> Any:
        """
        Dynamically load a Python module from a repository.
        
        This is similar to importlib.import_module() but with version control.
        The module is loaded into memory and cached for reuse.
        
        Args:
            repo_path: Repository path (e.g., "ix-hub/swe-agent").
            module_name: Module name to import (e.g., "agent" loads agent.py).
            revision: Git revision (tag, branch, or commit hash).
            force_reload: If True, re-import even if cached in memory.
            
        Returns:
            Loaded module object.
            
        Example:
            >>> hub = HubManager()
            >>> agent_module = hub.load_module(
            ...     "ix-hub/swe-agent",
            ...     "agent",
            ...     revision="v1.0.0"
            ... )
            >>> AgentClass = agent_module.SWEAgent
        """
        cache_key = (repo_path, revision, module_name)

        # Check in-memory cache
        if cache_key in self._module_cache and not force_reload:
            logger.info(f"Using in-memory cached module: {cache_key}")
            return self._module_cache[cache_key]

        # Get cached module path
        module_path = self.get_module_path(repo_path, revision, force_reload)

        # Load the module dynamically
        module_file = module_path / f"{module_name}.py"
        if not module_file.exists():
            raise FileNotFoundError(f"Module file not found: {module_file}\n"
                                    f"Looking for {module_name}.py in {module_path}")

        # Create a unique module name to avoid conflicts
        unique_module_name = f"interaxions_hub_{self._get_cache_key(repo_path, revision)}_{module_name}"

        # Load the module using importlib
        spec = importlib.util.spec_from_file_location(unique_module_name, module_file)
        if spec is None or spec.loader is None:
            raise ImportError(f"Failed to create module spec for {module_file}")

        module = importlib.util.module_from_spec(spec)

        # Add to sys.modules to support relative imports
        sys.modules[unique_module_name] = module

        try:
            spec.loader.exec_module(module)
        except Exception as e:
            # Clean up on error
            del sys.modules[unique_module_name]
            raise ImportError(f"Failed to execute module {module_file}: {e}")

        # Cache the loaded module
        self._module_cache[cache_key] = module

        logger.info(f"Successfully loaded module: {cache_key}")
        return module

    def clear_cache(self, repo_path: Optional[str] = None, revision: Optional[str] = None) -> None:
        """
        Clear cached modules.
        
        Args:
            repo_path: If provided, only clear this repository.
            revision: If provided (with repo_path), only clear this revision.
        """
        if repo_path is None:
            # Clear all
            logger.info("Clearing all cached modules")
            shutil.rmtree(self.cache_dir)
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            self._module_cache.clear()
        elif revision is None:
            # Clear all versions of a repository
            logger.info(f"Clearing all versions of {repo_path}")
            pattern = repo_path.replace("/", "--")
            for cache_path in self.cache_dir.glob(f"{pattern}--*"):
                shutil.rmtree(cache_path)
            # Clear from memory cache
            keys_to_remove = [k for k in self._module_cache.keys() if k[0] == repo_path]
            for key in keys_to_remove:
                del self._module_cache[key]
        else:
            # Clear specific version
            logger.info(f"Clearing {repo_path}@{revision}")
            cached_path = self._get_cached_path(repo_path, revision)
            if cached_path.exists():
                shutil.rmtree(cached_path)
            # Clear from memory cache
            keys_to_remove = [k for k in self._module_cache.keys() if k[0] == repo_path and k[1] == revision]
            for key in keys_to_remove:
                del self._module_cache[key]


# Global hub manager instance (singleton pattern)
_hub_manager: Optional[HubManager] = None


def get_hub_manager() -> HubManager:
    """
    Get the global hub manager instance.
    
    Similar to transformers' default cache directory pattern.
    
    Returns:
        Global HubManager instance.
    """
    global _hub_manager
    if _hub_manager is None:
        _hub_manager = HubManager()
    return _hub_manager
