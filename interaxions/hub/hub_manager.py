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

    def _get_cache_key(self, repo_name_or_path: str, revision: str) -> str:
        """
        Generate cache key for a repository and revision.
        
        Args:
            repo_name_or_path: Repository name or path (e.g., "ix-hub/swe-agent")
            revision: Git revision (tag, branch, or commit hash)
            
        Returns:
            Cache key string.
        """
        # Create a hash-based key
        key_str = f"{repo_name_or_path}@{revision}"
        key_hash = hashlib.sha256(key_str.encode()).hexdigest()[:16]
        # Make it human-readable too
        safe_path = repo_name_or_path.replace("/", "--")
        return f"{safe_path}--{revision}--{key_hash}"

    def _get_cached_path(self, repo_name_or_path: str, revision: str) -> Path:
        """
        Get the local cache path for a repository and revision.
        
        Args:
            repo_name_or_path: Repository name or path (e.g., "ix-hub/swe-agent")
            revision: Git revision (tag, branch, or commit hash)
            
        Returns:
            Local cache directory path.
        """
        cache_key = self._get_cache_key(repo_name_or_path, revision)
        return self.cache_dir / cache_key

    def _get_lock_file(self, repo_name_or_path: str, revision: str) -> Path:
        """
        Get the lock file path for a repository and revision.
        
        Args:
            repo_name_or_path: Repository name or path
            revision: Git revision
            
        Returns:
            Lock file path.
        """
        cache_key = self._get_cache_key(repo_name_or_path, revision)
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

    def _resolve_repo_path(
        self,
        repo_name_or_path: str,
        username: Optional[str] = None,
        token: Optional[str] = None,
    ) -> Path:
        """
        Resolve repository name or path to absolute path with optional authentication.
        
        Supports:
        - Relative paths (e.g., "ix-hub/swe-agent")
        - Absolute paths (e.g., "/path/to/ix-hub/swe-agent")
        - Remote paths (e.g., "username/repo" -> downloads from IX_ENDPOINT or GitHub)
        
        Args:
            repo_name_or_path: Repository name or path.
            username: Username for private repository authentication
            token: Token/password for private repository authentication
            
        Returns:
            Absolute path to the repository.
            
        Raises:
            FileNotFoundError: If repository path doesn't exist.
        """
        path = Path(repo_name_or_path)

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
            raise FileNotFoundError(f"Repository not found: {repo_name_or_path}\n"
                                    f"Tried: {full_path}\n"
                                    f"Working directory: {Path.cwd()}\n"
                                    f"Remote download disabled (IX_OFFLINE=true)")

        # Try to download from remote with authentication if provided
        logger.info(f"Local path not found, trying remote: {repo_name_or_path}")
        git_url = self._to_git_url(repo_name_or_path, username, token)
        return self._clone_remote_repo(git_url, repo_name_or_path)

    def _to_git_url(
        self,
        repo_name_or_path: str,
        username: Optional[str] = None,
        token: Optional[str] = None,
    ) -> str:
        """
        Convert a repository name or path to a Git URL with optional authentication.
        
        Uses IX_ENDPOINT environment variable if set, otherwise defaults to GitHub.
        
        Args:
            repo_name_or_path: Repository name or path (e.g., "username/repo")
            username: Username for private repository authentication
            token: Token/password for private repository authentication
            
        Returns:
            Git URL with embedded authentication if credentials provided.
            
        Examples:
            Public repository:
                "username/repo" -> "https://github.com/username/repo.git"
            
            Private repository with auth:
                "company/repo", "user", "token" -> "https://user:token@github.com/company/repo.git"
            
            With IX_ENDPOINT:
                IX_ENDPOINT="https://gitlab.company.com"
                "team/repo", "user", "token" -> "https://user:token@gitlab.company.com/team/repo.git"
        """
        # Check for custom endpoint
        endpoint = os.getenv("IX_ENDPOINT")
        if endpoint:
            base_url = endpoint.rstrip('/')
        else:
            base_url = "https://github.com"

        # Construct URL with optional authentication
        if username and token:
            # Extract protocol and host from base_url
            if base_url.startswith("http://"):
                protocol = "http"
                host = base_url[7:]  # Remove "http://"
            elif base_url.startswith("https://"):
                protocol = "https"
                host = base_url[8:]  # Remove "https://"
            else:
                # Assume https if no protocol specified
                protocol = "https"
                host = base_url

            # Construct authenticated URL: protocol://username:token@host/repo.git
            return f"{protocol}://{username}:{token}@{host}/{repo_name_or_path}.git"
        else:
            # No authentication - public repository
            return f"{base_url}/{repo_name_or_path}.git"

    def _clone_remote_repo(self, git_url: str, repo_name_or_path: str) -> Path:
        """
        Clone a remote Git repository to cache (with file lock protection).
        
        If the repository already exists, fetch the latest changes from remote.
        
        Args:
            git_url: Git URL to clone from
            repo_name_or_path: Repository name or path (e.g., "ix-hub/swe-agent")
                              Used for creating human-readable cache directory
            
        Returns:
            Path to the cloned repository
            
        Raises:
            RuntimeError: If git clone fails
        """
        # Sanitize repo name for filesystem: replace / with --
        # Examples:
        #   ix-hub/swe-agent -> repos--ix-hub--swe-agent
        #   company/private-repo -> repos--company--private-repo
        safe_name = repo_name_or_path.replace('/', '--')
        clone_dir = self.cache_dir / f"repos--{safe_name}"

        # Fast path: check if already cloned
        if clone_dir.exists():
            logger.info(f"Remote repository already cached: {clone_dir}")
            # Fetch latest changes from remote (non-blocking, best effort)
            self._update_remote_repo(clone_dir)
            return clone_dir

        # Need to clone - acquire lock for atomic operation
        lock_file = self.cache_dir / f"repos--{safe_name}.lock"
        lock_fd = None

        try:
            lock_fd = self._acquire_lock(lock_file)

            # Double-check: another process may have cloned while we waited
            if clone_dir.exists():
                logger.info(f"Using cached remote repository (cloned by another process): {clone_dir}")
                self._update_remote_repo(clone_dir)
                return clone_dir

            logger.info(f"Cloning remote repository: {git_url}")
            logger.info(f"This may take a while...")

            # Clone repository (full clone to allow fetching updates)
            subprocess.run(
                ["git", "clone", "--quiet", git_url, str(clone_dir)],
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

    def _update_remote_repo(self, repo_path: Path) -> None:
        """
        Update a remote repository by fetching latest changes.
        
        This is a best-effort operation - if it fails (e.g., network issue),
        we just log a warning and continue with the cached version.
        
        Args:
            repo_path: Path to the local clone of remote repository
        """
        try:
            logger.info(f"Fetching latest changes from remote for {repo_path}")

            # Fetch latest changes
            subprocess.run(
                ["git", "fetch", "origin"],
                cwd=repo_path,
                capture_output=True,
                text=True,
                check=True,
                timeout=30,  # 30 second timeout
            )

            # Update HEAD to match origin
            default_branch = self._get_default_branch(repo_path)
            subprocess.run(
                ["git", "reset", "--hard", f"origin/{default_branch}"],
                cwd=repo_path,
                capture_output=True,
                text=True,
                check=True,
            )

            logger.info("Successfully fetched and updated to latest changes")
        except subprocess.TimeoutExpired:
            logger.warning(f"Git fetch timed out for {repo_path}, using cached version")
        except subprocess.CalledProcessError as e:
            logger.warning(f"Failed to fetch updates for {repo_path}: {e.stderr if e.stderr else str(e)}")
            logger.warning("Continuing with cached version")
        except Exception as e:
            logger.warning(f"Unexpected error during git fetch: {e}")
            logger.warning("Continuing with cached version")

    def _get_default_branch(self, source_path: Path) -> str:
        """
        Get the default branch of a local git repository.
        
        This is used for local repositories that have already been cloned.
        For remote repositories, git clone without --branch automatically uses the default branch.
        
        Args:
            source_path: Path to the local git repository.
            
        Returns:
            Name of the default branch (e.g., "main", "master", "develop").
            Falls back to "HEAD" if unable to determine.
        """
        # Check if it's a git repository
        if not (source_path / ".git").exists():
            logger.warning(f"Not a git repository: {source_path}, using 'HEAD'")
            return "HEAD"

        try:
            # Get the default branch by checking what origin/HEAD points to
            result = subprocess.run(
                ["git", "symbolic-ref", "refs/remotes/origin/HEAD"],
                cwd=source_path,
                capture_output=True,
                text=True,
                check=True,
            )
            # Output format: refs/remotes/origin/main
            default_ref = result.stdout.strip()
            default_branch = default_ref.split("/")[-1]
            logger.info(f"Detected default branch: {default_branch}")
            return default_branch
        except subprocess.CalledProcessError:
            # If symbolic-ref fails, try to get current HEAD
            logger.debug("symbolic-ref failed, trying to get current HEAD")
            try:
                result = subprocess.run(
                    ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                    cwd=source_path,
                    capture_output=True,
                    text=True,
                    check=True,
                )
                current_branch = result.stdout.strip()
                if current_branch and current_branch != "HEAD":
                    logger.info(f"Using current branch as default: {current_branch}")
                    return current_branch
            except subprocess.CalledProcessError:
                pass

        # Fallback to "HEAD"
        logger.warning(f"Could not determine default branch for {source_path}, using 'HEAD'")
        return "HEAD"

    def _get_local_commit_hash(self, source_path: Path) -> str:
        """
        Get the current commit hash from a local git repository.
        
        This always uses local HEAD, which includes:
        - Committed local changes
        - Local commits not yet pushed to remote
        
        This method is simple and fast - no remote fetch needed.
        
        Args:
            source_path: Path to the local git repository.
            
        Returns:
            Current commit hash (short form, 8 characters).
            Falls back to "HEAD" if unable to determine or not a git repo.
        """
        # Check if it's a git repository
        if not (source_path / ".git").exists():
            logger.warning(f"Not a git repository: {source_path}, using 'HEAD'")
            return "HEAD"

        try:
            result = subprocess.run(
                ["git", "rev-parse", "--short=8", "HEAD"],
                cwd=source_path,
                capture_output=True,
                text=True,
                check=True,
            )
            commit_hash = result.stdout.strip()
            logger.info(f"Local HEAD commit hash: {commit_hash}")
            return commit_hash
        except subprocess.CalledProcessError as e:
            logger.warning(f"Could not determine commit hash for {source_path}: {e}, using 'HEAD'")
            return "HEAD"

    def _checkout_revision(
        self,
        source_path: Path,
        revision: str,
        target_dir: Path,
    ) -> None:
        """
        Checkout a specific revision of a repository to target directory.
        
        Uses git worktree to create an isolated checkout without affecting
        the original repository.
        
        Args:
            source_path: Path to the local git repository.
            revision: Git revision (tag, branch, commit).
            target_dir: Target directory for checkout.
            
        Raises:
            RuntimeError: If git operations fail.
        """
        # Check if it's a git repository
        if not (source_path / ".git").exists():
            # Not a git repo, just copy the directory
            logger.info(f"Not a git repository, copying directory: {source_path}")
            shutil.copytree(source_path, target_dir, dirs_exist_ok=True)
            return

        try:
            # Use git archive to export specific revision
            # This is cleaner than worktree and doesn't modify the source repo
            logger.info(f"Checking out revision '{revision}' from {source_path}")

            # First, resolve the revision to a commit hash
            result = subprocess.run(
                ["git", "rev-parse", revision],
                cwd=source_path,
                capture_output=True,
                text=True,
                check=True,
            )
            commit_hash = result.stdout.strip()
            logger.info(f"Resolved '{revision}' to commit {commit_hash}")

            # Create target directory
            target_dir.mkdir(parents=True, exist_ok=True)

            # Use git archive to export the tree
            # Create the archive process
            archive_process = subprocess.Popen(
                ["git", "archive", commit_hash],
                cwd=source_path,
                stdout=subprocess.PIPE,
            )

            # Create the tar extraction process
            tar_process = subprocess.Popen(
                ["tar", "-x", "-C", str(target_dir)],
                stdin=archive_process.stdout,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

            # Allow archive_process to receive a SIGPIPE if tar_process exits
            if archive_process.stdout:
                archive_process.stdout.close()

            # Wait for completion
            tar_output, tar_error = tar_process.communicate()

            # Check return codes
            if archive_process.returncode is None:
                archive_process.wait()
            if archive_process.returncode != 0:
                raise subprocess.CalledProcessError(
                    archive_process.returncode,
                    ["git", "archive", commit_hash],
                )
            if tar_process.returncode != 0:
                raise subprocess.CalledProcessError(
                    tar_process.returncode,
                    ["tar", "-x", "-C", str(target_dir)],
                    stderr=tar_error,
                )

            logger.info(f"Successfully checked out to {target_dir}")

        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Failed to checkout revision '{revision}' from {source_path}:\n"
                               f"Error: {e.stderr if hasattr(e, 'stderr') else str(e)}")

    def get_module_path(
        self,
        repo_name_or_path: str,
        revision: Optional[str] = None,
        force_reload: bool = False,
        username: Optional[str] = None,
        token: Optional[str] = None,
    ) -> Path:
        """
        Get the path to a cached module for a specific revision with optional authentication.
        
        This method is thread-safe and process-safe:
        1. Checks if the revision is already cached
        2. If not, acquires a file lock to ensure atomic download
        3. Double-checks cache after acquiring lock (another process may have downloaded)
        4. Downloads/checks out if still not cached
        5. Returns the cached path
        
        When revision is None:
        - If repo exists locally: Uses local HEAD commit hash
        - If repo doesn't exist locally: Downloads from remote, then uses local HEAD
        - This ensures local changes (including uncommitted) are always detected
        
        Strategy:
        1. Resolve repo path (downloads from remote if not exists locally)
        2. Once local, always use local HEAD commit hash
        3. Different commit hashes create separate cache entries
        
        Args:
            repo_name_or_path: Repository name or path (e.g., "ix-hub/swe-agent").
            revision: Git revision (tag, branch, or commit hash). 
                     If None, automatically resolves to local HEAD commit hash.
            force_reload: If True, re-download even if cached.
            username: Username for private repository authentication
            token: Token/password for private repository authentication
            
        Returns:
            Path to the cached module directory.
        """
        # If revision is None, resolve to latest commit hash from local HEAD
        if revision is None:
            # First resolve the repo path (this will clone from remote if not exists locally)
            source_path = self._resolve_repo_path(repo_name_or_path, username, token)

            # Now that we have a local path, always use local HEAD commit hash
            # This works for:
            # - Original local repositories
            # - Remote repositories cloned to local
            # - All detect local changes/new commits
            revision = self._get_local_commit_hash(source_path)
            logger.info(f"Resolved to local commit hash: {revision}")

        cached_path = self._get_cached_path(repo_name_or_path, revision)

        # Fast path: check if already cached (no lock needed for read)
        if cached_path.exists() and not force_reload:
            logger.info(f"Using cached module: {cached_path}")
            return cached_path

        # Need to download - acquire lock for atomic operation
        lock_file = self._get_lock_file(repo_name_or_path, revision)
        lock_fd = None

        try:
            lock_fd = self._acquire_lock(lock_file)

            # Double-check: another process may have downloaded while we waited for lock
            if cached_path.exists() and not force_reload:
                logger.info(f"Using cached module (downloaded by another process): {cached_path}")
                return cached_path

            # Resolve source repository with authentication
            source_path = self._resolve_repo_path(repo_name_or_path, username, token)

            # Clean up existing cache if force_reload
            if cached_path.exists() and force_reload:
                logger.info(f"Force reload: removing cached module {cached_path}")
                shutil.rmtree(cached_path)

            # Checkout revision to cache
            logger.info(f"Caching module {repo_name_or_path}@{revision} to {cached_path}")
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

    def load_module(
        self,
        repo_name_or_path: str,
        module_name: str,
        revision: Optional[str] = None,
        force_reload: bool = False,
    ) -> Any:
        """
        Dynamically load a Python module from a repository.
        
        This is similar to importlib.import_module() but with version control.
        The module is loaded into memory and cached for reuse.
        
        Args:
            repo_name_or_path: Repository name or path (e.g., "ix-hub/swe-agent").
            module_name: Module name to import (e.g., "agent" loads agent.py).
            revision: Git revision (tag, branch, or commit hash).
                     If None, uses the repository's default branch.
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
        cache_key = (repo_name_or_path, revision, module_name)

        # Check in-memory cache
        if cache_key in self._module_cache and not force_reload:
            logger.info(f"Using in-memory cached module: {cache_key}")
            return self._module_cache[cache_key]

        # Get cached module path
        module_path = self.get_module_path(repo_name_or_path, revision, force_reload)

        # Load the module dynamically
        module_file = module_path / f"{module_name}.py"
        if not module_file.exists():
            raise FileNotFoundError(f"Module file not found: {module_file}\n"
                                    f"Looking for {module_name}.py in {module_path}")

        # Create a unique module name to avoid conflicts
        unique_module_name = f"interaxions_hub_{self._get_cache_key(repo_name_or_path, revision)}_{module_name}"

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

    def clear_cache(
        self,
        repo_name_or_path: Optional[str] = None,
        revision: Optional[str] = None,
    ) -> None:
        """
        Clear cached modules.
        
        Args:
            repo_name_or_path: If provided, only clear this repository.
            revision: If provided (with repo_name_or_path), only clear this revision.
        """
        if repo_name_or_path is None:
            # Clear all
            logger.info("Clearing all cached modules")
            shutil.rmtree(self.cache_dir)
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            self._module_cache.clear()
        elif revision is None:
            # Clear all versions of a repository
            logger.info(f"Clearing all versions of {repo_name_or_path}")
            pattern = repo_name_or_path.replace("/", "--")
            for cache_path in self.cache_dir.glob(f"{pattern}--*"):
                shutil.rmtree(cache_path)
            # Clear from memory cache
            keys_to_remove = [k for k in self._module_cache.keys() if k[0] == repo_name_or_path]
            for key in keys_to_remove:
                del self._module_cache[key]
        else:
            # Clear specific version
            logger.info(f"Clearing {repo_name_or_path}@{revision}")
            cached_path = self._get_cached_path(repo_name_or_path, revision)
            if cached_path.exists():
                shutil.rmtree(cached_path)
            # Clear from memory cache
            keys_to_remove = [k for k in self._module_cache.keys() if k[0] == repo_name_or_path and k[1] == revision]
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
