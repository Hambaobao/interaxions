"""
Auto classes for convenient loading of scaffolds, environments, and workflows.

Similar to transformers' AutoModel, AutoTokenizer, etc.
These classes automatically handle module loading and instantiation from
remote or local repositories. All repos must have an ix.py entry file.

Convention:
    Every ix-hub repository must contain:
    - config.yaml  (with repo_type: scaffold | environment | workflow)
    - ix.py        (with exactly one class inheriting from the appropriate Base class)

Environment Variables:
    IX_HOME: Base directory for Interaxions data (default: ~/.interaxions)
    IX_HUB_CACHE: Hub cache directory (default: $IX_HOME/hub)
"""

import copy
import importlib
import inspect
import logging

from pathlib import Path
from typing import Any, Dict, Optional, Tuple, Type, TypeVar, Union

from interaxions.hub.hub_manager import get_hub_manager
from interaxions.scaffolds.base_scaffold import BaseScaffold
from interaxions.environments.base_environment import BaseEnvironment
from interaxions.workflows.base_workflow import BaseWorkflow
from interaxions.tasks.base_task import BaseTask

logger = logging.getLogger(__name__)

T = TypeVar("T")


class _AutoBase:
    """
    Private base class providing shared loading logic for all Auto classes.

    Not intended for direct use. Subclass and set BASE_CLASS to use.
    """

    BASE_CLASS: Type = None         # Set by each subclass
    ENTRY_MODULE: str = "ix"        # All repos must have ix.py

    # Instance cache: key=(repo_name_or_path, revision), value=instance
    _instance_cache: Dict[Tuple[str, str], Any] = {}

    @classmethod
    def from_repo(
        cls,
        repo_name_or_path: Union[str, Path],
        revision: Optional[str] = None,
        username: Optional[str] = None,
        token: Optional[str] = None,
        force_reload: bool = False,
    ):
        """
        Load a class instance from a remote or local repository.

        The repository must contain:
        - config.yaml with repo_type field
        - ix.py with exactly one class inheriting from the appropriate base

        Args:
            repo_name_or_path: Repository name or local path.
                - Remote: "ix-hub/swe-bench" or "username/repo"
                - Local:  "./my-repo" or Path("/abs/path/to/repo")
            revision: Git revision (tag, branch, or commit hash).
                      If None, resolves to the latest commit of the default branch.
            username: Username for private repository authentication.
            token: Token/password for private repository authentication.
            force_reload: If True, bypass cache and re-download.

        Returns:
            Instance of the discovered class loaded from the repository.
        """
        repo_str = str(repo_name_or_path)

        # Fast path: cache hit for pinned revisions
        if revision is not None:
            cache_key = (repo_str, revision)
            if cache_key in cls._instance_cache and not force_reload:
                logger.info(f"Using cached instance: {cache_key}")
                return copy.deepcopy(cls._instance_cache[cache_key])

        instance = cls._load_dynamic(repo_str, revision, username, token, force_reload)

        # Cache only pinned revisions (revision=None always gets latest)
        if revision is not None:
            cache_key = (repo_str, revision)
            cls._instance_cache[cache_key] = instance
            logger.info(f"Cached instance: {cache_key}")
            return copy.deepcopy(instance)

        return instance

    @classmethod
    def _load_dynamic(
        cls,
        repo_name_or_path: str,
        revision: Optional[str],
        username: Optional[str] = None,
        token: Optional[str] = None,
        force_reload: bool = False,
    ):
        """Load an instance from a remote or local repository via hub_manager."""
        hub_manager = get_hub_manager()

        # Download/locate the repository
        module_path = hub_manager.get_module_path(
            repo_name_or_path,
            revision,
            force_reload=force_reload,
            username=username,
            token=token,
        )

        logger.info(f"Loading {cls.BASE_CLASS.__name__} from {repo_name_or_path}@{revision}")
        logger.info(f"Module path: {module_path}")

        # Load ix.py from the repository
        module = hub_manager.load_module(
            repo_name_or_path,
            cls.ENTRY_MODULE,
            revision,
            force_reload=force_reload,
        )

        # Discover the target class in ix.py
        target_class = cls._discover_class(module)
        logger.info(f"Using class: {target_class.__name__}")

        # Instantiate using from_repo() which loads config.yaml
        instance = target_class.from_repo(module_path)
        logger.info(f"Successfully loaded: {target_class.__name__}")
        return instance

    @classmethod
    def _discover_class(cls, module: Any) -> type:
        """
        Auto-discover the target class in ix.py.

        Looks for exactly one class that inherits from BASE_CLASS.

        Args:
            module: Python module object (loaded from ix.py).

        Returns:
            The discovered class.

        Raises:
            ValueError: If no class found or multiple classes found.
        """
        base = cls.BASE_CLASS
        found = [
            obj
            for name, obj in inspect.getmembers(module)
            if inspect.isclass(obj) and issubclass(obj, base) and obj is not base
        ]

        if len(found) == 0:
            available = [name for name, obj in inspect.getmembers(module) if inspect.isclass(obj)]
            raise ValueError(
                f"No class inheriting from {base.__name__} found in ix.py.\n"
                f"Available classes: {available}"
            )

        if len(found) > 1:
            names = [c.__name__ for c in found]
            raise ValueError(
                f"Multiple classes inheriting from {base.__name__} found in ix.py: {names}\n"
                f"Please ensure only one class per ix.py."
            )

        return found[0]


class AutoScaffold(_AutoBase):
    """
    Auto class for loading scaffold task executors from repositories.

    Discovers and loads the class inheriting from BaseScaffold in a repo's ix.py.

    Example:
        >>> scaffold = AutoScaffold.from_repo("ix-hub/swe-agent")
        >>> scaffold = AutoScaffold.from_repo("ix-hub/swe-agent", revision="v1.0.0")
        >>> scaffold = AutoScaffold.from_repo("./local-agent")  # local path for testing

    Note:
        For IDE support, add a type hint:
        >>> from my_scaffold.ix import MySWEAgent
        >>> scaffold: MySWEAgent = AutoScaffold.from_repo("ix-hub/swe-agent")
    """

    BASE_CLASS = BaseScaffold
    _instance_cache: Dict[Tuple[str, str], BaseScaffold] = {}

    @classmethod
    def from_repo(
        cls,
        repo_name_or_path: Union[str, Path],
        revision: Optional[str] = None,
        username: Optional[str] = None,
        token: Optional[str] = None,
        force_reload: bool = False,
    ) -> BaseScaffold:
        return super().from_repo(repo_name_or_path, revision, username, token, force_reload)


class AutoEnvironment(_AutoBase):
    """
    Auto class for loading environment task executors from repositories.

    Discovers and loads the class inheriting from BaseEnvironment in a repo's ix.py.
    The returned object has two key methods:
    - get(id) -> Environment: fetch instance data (credentials via env vars)
    - create_task(job) -> hera.Task: create the Argo evaluation task

    Example:
        >>> env_task = AutoEnvironment.from_repo("ix-hub/swe-bench")
        >>> env_task = AutoEnvironment.from_repo("ix-hub/swe-bench", revision="v2.0.0")
        >>> env_task = AutoEnvironment.from_repo("./local-bench")  # local path for testing

        >>> env = env_task.get("django__django-12345")
        >>> env.id, env.type, env.data.keys()

    Note:
        For IDE support, add a type hint:
        >>> from my_env.ix import MySWEBench
        >>> env_task: MySWEBench = AutoEnvironment.from_repo("ix-hub/swe-bench")
    """

    BASE_CLASS = BaseEnvironment
    _instance_cache: Dict[Tuple[str, str], BaseEnvironment] = {}

    @classmethod
    def from_repo(
        cls,
        repo_name_or_path: Union[str, Path],
        revision: Optional[str] = None,
        username: Optional[str] = None,
        token: Optional[str] = None,
        force_reload: bool = False,
    ) -> BaseEnvironment:
        return super().from_repo(repo_name_or_path, revision, username, token, force_reload)


class AutoWorkflow(_AutoBase):
    """
    Auto class for loading workflow orchestrators from repositories.

    Discovers and loads the class inheriting from BaseWorkflow in a repo's ix.py.
    The returned object has create_workflow(job) which builds the full Argo Workflow.

    Example:
        >>> workflow = AutoWorkflow.from_repo("ix-hub/swe-rollout-verify")
        >>> workflow = AutoWorkflow.from_repo("ix-hub/swe-rollout-verify", revision="v1.0.0")
        >>> workflow = AutoWorkflow.from_repo("./local-workflow")  # local path for testing

        >>> argo_workflow = workflow.create_workflow(job)
        >>> argo_workflow.create()  # submit to Argo

    Note:
        For IDE support, add a type hint:
        >>> from my_workflow.ix import MyWorkflow
        >>> workflow: MyWorkflow = AutoWorkflow.from_repo("ix-hub/swe-rollout-verify")
    """

    BASE_CLASS = BaseWorkflow
    _instance_cache: Dict[Tuple[str, str], BaseWorkflow] = {}

    @classmethod
    def from_repo(
        cls,
        repo_name_or_path: Union[str, Path],
        revision: Optional[str] = None,
        username: Optional[str] = None,
        token: Optional[str] = None,
        force_reload: bool = False,
    ) -> BaseWorkflow:
        return super().from_repo(repo_name_or_path, revision, username, token, force_reload)


class AutoTask(_AutoBase):
    """
    Auto class for loading generic Argo task executors from repositories.

    Discovers and loads the class inheriting from BaseTask in a repo's ix.py.
    Unlike AutoScaffold (agent runner) and AutoEnvironment (eval environment),
    AutoTask carries no assumptions about job schemas or environment data.
    It is suitable for arbitrary Argo tasks: data preprocessing, model training,
    result aggregation, notifications, and so on.

    The returned object's create_task(**kwargs) signature is defined entirely
    by the concrete implementation — pass whatever the task needs.

    Example:
        >>> task = AutoTask.from_repo("ix-hub/data-preprocess")
        >>> task = AutoTask.from_repo("ix-hub/data-preprocess", revision="v1.0.0")
        >>> task = AutoTask.from_repo("./local-task")  # local path for testing

        >>> argo_task = task.create_task(dataset="swe-bench", output_bucket="s3://my-bucket")

        >>> # Freely compose with other tasks in a workflow — no XJob required
        >>> with Workflow(name="my-pipeline") as w:
        ...     t1 = preprocess_task.create_task(dataset="swe-bench")
        ...     t2 = train_task.create_task(model="gpt-4o")
        ...     t1 >> t2

    Note:
        For IDE support, add a type hint:
        >>> from my_task.ix import MyPreprocessTask
        >>> task: MyPreprocessTask = AutoTask.from_repo("ix-hub/data-preprocess")
    """

    BASE_CLASS = BaseTask
    _instance_cache: Dict[Tuple[str, str], BaseTask] = {}

    @classmethod
    def from_repo(
        cls,
        repo_name_or_path: Union[str, Path],
        revision: Optional[str] = None,
        username: Optional[str] = None,
        token: Optional[str] = None,
        force_reload: bool = False,
    ) -> BaseTask:
        return super().from_repo(repo_name_or_path, revision, username, token, force_reload)
