"""
Auto classes for convenient loading of agents and environments.

Similar to transformers' AutoModel, AutoTokenizer, etc.
These classes automatically handle module loading and instantiation.

Environment Variables:
    IX_HOME: Base directory for Interaxions data (default: ~/.interaxions)
    IX_HUB_CACHE: Hub cache directory (default: $IX_HOME/hub)
"""

import importlib
import logging
from pathlib import Path
from typing import Any, Optional, Union

from interaxions.hub.hub_manager import get_hub_manager
from interaxions.scaffolds.base_scaffold import BaseScaffold
from interaxions.environments.base_environment import BaseEnvironment, BaseEnvironmentFactory
from interaxions.workflows.base_workflow import BaseWorkflow

logger = logging.getLogger(__name__)


class AutoScaffold:
    """
    Auto class for loading agent scaffolds from repositories.
    
    An agent scaffold may internally create and manage single or multiple agents.
    This class automatically:
    1. Loads the module from the specified repository and revision
    2. Discovers the agent class in the module
    3. Loads configuration using from_repo()
    4. Returns an instantiated scaffold (which may contain one or more agents)
    
    Example:
        >>> # Load builtin scaffold
        >>> scaffold = AutoScaffold.from_repo("swe-agent")
        >>> 
        >>> # Load from remote/local repository
        >>> scaffold = AutoScaffold.from_repo("ix-hub/multi-agent-team", revision="v1.0.0")
        >>> 
        >>> # Use the scaffold (internally may create multiple agents)
        >>> task = scaffold.create_task(job)
    
    Note:
        For better IDE support (method navigation, autocomplete), you can add type hints:
        
        >>> from interaxions.scaffolds.swe_agent.scaffold import SWEAgent
        >>> scaffold: SWEAgent = AutoScaffold.from_repo("swe-agent")
        >>> # Now IDE can navigate to SWEAgent methods
    """

    @classmethod
    def from_repo(
        cls,
        repo_name_or_path: Union[str, Path],
        revision: Optional[str] = None,
        username: Optional[str] = None,
        token: Optional[str] = None,
        force_reload: bool = False,
    ) -> BaseScaffold:
        """
        Load an agent from a repository with optional authentication for private repos.
        
        The loading priority:
        1. Try builtin (interaxions.scaffolds.*)
        2. If not builtin, use dynamic loading (remote/local)
        
        Args:
            repo_name_or_path: Repository name or path. Examples:
                - "swe-agent" (builtin scaffold from interaxions.scaffolds.swe_agent)
                - "my-agent" (local repo or remote if builtin not found)
                - "ix-hub/swe-agent" (remote/local repository)
                - "./my-agent" or Path("./my-agent") (local path)
            revision: Git revision (tag, branch, or commit hash). Default: None.
                If None, automatically resolves to the latest commit hash of the default branch.
                Only used for remote/local repositories (ignored for builtin).
            username: Username for private repository authentication
            token: Token/password for private repository authentication
            force_reload: If True, re-download even if cached. Only applies to remote/local repositories.
            
        Returns:
            Loaded agent instance.
            
        Example:
            >>> # Load builtin scaffold
            >>> scaffold = AutoScaffold.from_repo("swe-agent")
            >>> 
            >>> # Load from remote repository (latest commit)
            >>> scaffold = AutoScaffold.from_repo("ix-hub/swe-agent")
            >>> 
            >>> # Load specific version
            >>> scaffold = AutoScaffold.from_repo("ix-hub/swe-agent", revision="v1.0.0")
            >>> 
            >>> # Force reload to get updates
            >>> scaffold = AutoScaffold.from_repo("ix-hub/swe-agent", force_reload=True)
            >>> 
            >>> # Load from private repository
            >>> scaffold = AutoScaffold.from_repo(
            ...     "company/private-agent",
            ...     username="user",
            ...     token="ghp_xxxxx"
            ... )
        """
        # Try builtin first
        try:
            return cls._load_builtin_agent(str(repo_name_or_path))
        except ImportError:
            # Not builtin, use dynamic loading
            pass

        # Dynamic loading (remote/local) with authentication support
        return cls._load_dynamic_agent(str(repo_name_or_path), revision, username, token, force_reload)

    @classmethod
    def _load_builtin_agent(cls, name: str) -> BaseScaffold:
        """
        Load a builtin scaffold from interaxions.scaffolds.
        
        Args:
            name: Agent name (e.g., "swe-agent" or "swe_agent")
            
        Returns:
            Agent instance with default configuration.
            
        Raises:
            ImportError: If builtin agent not found.
        """
        # Skip if it looks like a path (contains /, ., or ~)
        if any(char in name for char in ['/', '.', '~']):
            raise ImportError(f"'{name}' looks like a path, not a builtin agent name")

        # Convert name to module name (swe-agent -> swe_agent)
        module_name = name.replace("-", "_")

        # Try to import the builtin module (will raise ImportError if not found)
        module = importlib.import_module(f"interaxions.scaffolds.{module_name}")

        # Find agent class
        agent_class = cls._discover_agent_class(module)

        logger.info(f"Loaded builtin agent: {agent_class.__name__}")

        # Create instance with default config
        # Builtin scaffolds should have all config fields with defaults
        from interaxions.scaffolds.base_scaffold import BaseScaffoldConfig
        config_class = getattr(agent_class, "config_class", BaseScaffoldConfig)
        config = config_class()

        return agent_class(config=config)

    @classmethod
    def _load_dynamic_agent(
        cls,
        repo_name_or_path: str,
        revision: str,
        username: Optional[str] = None,
        token: Optional[str] = None,
        force_reload: bool = False,
    ) -> BaseScaffold:
        """
        Load an agent from a remote or local repository with optional authentication.
        
        Args:
            repo_name_or_path: Repository name or path (e.g., "ix-hub/swe-agent" or "./my-agent")
            revision: Git revision
            username: Username for private repository authentication
            token: Token/password for private repository authentication
            force_reload: If True, re-download even if cached
            
        Returns:
            Agent instance loaded from repository.
        """
        hub_manager = get_hub_manager()

        # Get the module path (handles caching and checkout) with authentication
        module_path = hub_manager.get_module_path(
            repo_name_or_path, revision, force_reload=force_reload, username=username, token=token
        )

        logger.info(f"Loading agent from {repo_name_or_path}@{revision}")
        logger.info(f"Module path: {module_path}")

        # Load the Python module dynamically
        agent_module = hub_manager.load_module(repo_name_or_path, "scaffold", revision, force_reload=force_reload)

        # Discover the agent class
        agent_class = cls._discover_agent_class(agent_module)

        logger.info(f"Using agent class: {agent_class.__name__}")

        # Load agent using from_repo()
        agent = agent_class.from_repo(module_path)

        logger.info(f"Successfully loaded agent: {agent_class.__name__}")
        return agent

    @staticmethod
    def _discover_agent_class(module: Any) -> type:
        """
        Auto-discover the agent class in a module.
        
        Looks for classes that inherit from BaseScaffold.
        
        Args:
            module: Python module object.
            
        Returns:
            Agent class.
            
        Raises:
            ValueError: If no agent class found or multiple found.
        """
        import inspect

        agent_classes = []
        for name, obj in inspect.getmembers(module):
            if (inspect.isclass(obj) and issubclass(obj, BaseScaffold) and obj is not BaseScaffold):
                agent_classes.append(obj)

        if len(agent_classes) == 0:
            raise ValueError(f"No agent class found in module.\n"
                             f"Expected a class inheriting from BaseScaffold.\n"
                             f"Available classes: {[name for name, obj in inspect.getmembers(module) if inspect.isclass(obj)]}")

        if len(agent_classes) > 1:
            class_names = [cls.__name__ for cls in agent_classes]
            raise ValueError(f"Multiple agent classes found: {class_names}\n"
                             f"Please ensure only one agent class per module.")

        return agent_classes[0]


class AutoEnvironmentFactory:
    """
    Auto class for loading environment factories from repositories.
    
    Similar to AutoScaffold and transformers.AutoTokenizer.
    
    Use this for batch operations (multiple environments from same repository).
    For single-use scenarios, consider using AutoEnvironment instead.
    
    Example:
        >>> # Load builtin environment (no "/" in path)
        >>> factory = AutoEnvironmentFactory.from_repo("swe-bench")
        >>> 
        >>> # Load from remote/local repository (contains "/")
        >>> factory = AutoEnvironmentFactory.from_repo("ix-hub/swe-bench", revision="v2.0.0")
        >>> 
        >>> # Create environment instances (efficient for batch)
        >>> env1 = factory.get_from_hf(environment_id="django-123", ...)
        >>> env2 = factory.get_from_hf(environment_id="flask-456", ...)  # Reuses factory
        >>> 
        >>> # Create verification tasks
        >>> task = env.create_task(job)
    
    Note:
        For better IDE support (method navigation, autocomplete), you can add type hints:
        
        >>> from interaxions.environments.swe_bench.env import SWEBenchFactory
        >>> factory: SWEBenchFactory = AutoEnvironmentFactory.from_repo("swe-bench")
        >>> # Now IDE can navigate to SWEBenchFactory methods
    """

    @classmethod
    def from_repo(
        cls,
        repo_name_or_path: Union[str, Path],
        revision: Optional[str] = None,
        username: Optional[str] = None,
        token: Optional[str] = None,
        force_reload: bool = False,
    ) -> BaseEnvironmentFactory:
        """
        Load an environment factory from a repository with optional authentication for private repos.
        
        The loading priority:
        1. Try builtin (interaxions.environments.*)
        2. If not builtin, use dynamic loading (remote/local)
        
        Args:
            repo_name_or_path: Repository name or path. Examples:
                - "swe-bench" (builtin environment from interaxions.environments.swe_bench)
                - "my-benchmark" (local repo or remote if builtin not found)
                - "ix-hub/swe-bench" (remote/local repository)
                - "./my-benchmark" or Path("./my-benchmark") (local path)
            revision: Git revision (tag, branch, or commit hash). Default: None.
                If None, automatically resolves to the latest commit hash of the default branch.
                Only used for remote/local repositories (ignored for builtin).
            username: Username for private repository authentication
            token: Token/password for private repository authentication
            force_reload: If True, re-download even if cached. Only applies to remote/local repositories.
            
        Returns:
            Loaded environment factory object.
            
        Example:
            >>> # Load builtin environment
            >>> factory = AutoEnvironmentFactory.from_repo("swe-bench")
            >>> 
            >>> # Load from remote repository (latest commit)
            >>> factory = AutoEnvironmentFactory.from_repo("ix-hub/swe-bench")
            >>> 
            >>> # Load specific version
            >>> factory = AutoEnvironmentFactory.from_repo("ix-hub/swe-bench", revision="v2.0.0")
            >>> 
            >>> # Force reload to get updates
            >>> factory = AutoEnvironmentFactory.from_repo("ix-hub/swe-bench", force_reload=True)
            >>> 
            >>> # Load from private repository
            >>> factory = AutoEnvironmentFactory.from_repo(
            ...     "company/private-bench",
            ...     username="user",
            ...     token="ghp_xxxxx"
            ... )
            >>> 
            >>> # Get environment instances
            >>> env = factory.get_from_hf(environment_id="...", dataset="...", split="test")
        """
        # Try builtin first
        try:
            return cls._load_builtin_environment(str(repo_name_or_path))
        except ImportError:
            # Not builtin, use dynamic loading
            pass

        # Dynamic loading (remote/local) with authentication support
        return cls._load_dynamic_environment(str(repo_name_or_path), revision, username, token, force_reload)

    @classmethod
    def _load_builtin_environment(cls, name: str) -> BaseEnvironmentFactory:
        """
        Load a builtin environment from interaxions.environments.
        
        Args:
            name: Environment name (e.g., "swe-bench" or "swebench")
            
        Returns:
            Environment factory instance with default configuration.
            
        Raises:
            ImportError: If builtin environment not found.
        """
        # Skip if it looks like a path (contains /, ., or ~)
        if any(char in name for char in ['/', '.', '~']):
            raise ImportError(f"'{name}' looks like a path, not a builtin environment name")

        # Convert name to module name (swe-bench -> swe_bench)
        module_name = name.replace("-", "_")

        # Try to import the builtin module (will raise ImportError if not found)
        module = importlib.import_module(f"interaxions.environments.{module_name}")

        # Find environment factory class
        env_class = cls._discover_env_class(module)

        logger.info(f"Loaded builtin environment: {env_class.__name__}")

        # Create instance with default config
        # Builtin environments should have all config fields with defaults
        from interaxions.environments.base_environment import BaseEnvironmentConfig
        config_class = getattr(env_class, "config_class", BaseEnvironmentConfig)
        config = config_class()

        return env_class(config=config)

    @classmethod
    def _load_dynamic_environment(
        cls,
        repo_name_or_path: str,
        revision: str,
        username: Optional[str] = None,
        token: Optional[str] = None,
        force_reload: bool = False,
    ) -> BaseEnvironmentFactory:
        """
        Load an environment from a remote or local repository with optional authentication.
        
        Args:
            repo_name_or_path: Repository name or path (e.g., "ix-hub/swe-bench" or "./my-benchmark")
            revision: Git revision
            username: Username for private repository authentication
            token: Token/password for private repository authentication
            force_reload: If True, re-download even if cached
            
        Returns:
            Environment factory instance loaded from repository.
        """
        hub_manager = get_hub_manager()

        # Get the module path (handles caching and checkout) with authentication
        module_path = hub_manager.get_module_path(
            repo_name_or_path, revision, force_reload=force_reload, username=username, token=token
        )

        logger.info(f"Loading environment factory from {repo_name_or_path}@{revision}")
        logger.info(f"Module path: {module_path}")

        # Load the Python module dynamically
        env_module = hub_manager.load_module(repo_name_or_path, "env", revision, force_reload=force_reload)

        # Discover the environment factory class
        env_class = cls._discover_env_class(env_module)

        logger.info(f"Using environment factory class: {env_class.__name__}")

        # Load environment factory using from_repo()
        env_factory = env_class.from_repo(module_path)

        logger.info(f"Successfully loaded environment factory: {env_class.__name__}")
        return env_factory

    @staticmethod
    def _discover_env_class(module: Any) -> type:
        """
        Auto-discover the environment factory class in a module.
        
        Looks for classes that inherit from BaseEnvironmentFactory.
        
        Args:
            module: Python module object.
            
        Returns:
            Environment factory class.
            
        Raises:
            ValueError: If no environment factory class found or multiple found.
        """
        import inspect

        env_classes = []
        for name, obj in inspect.getmembers(module):
            if (inspect.isclass(obj) and issubclass(obj, BaseEnvironmentFactory) and obj is not BaseEnvironmentFactory):
                env_classes.append(obj)

        if len(env_classes) == 0:
            raise ValueError(f"No environment factory class found in module.\n"
                             f"Expected a class inheriting from BaseEnvironmentFactory.\n"
                             f"Available classes: {[name for name, obj in inspect.getmembers(module) if inspect.isclass(obj)]}")

        if len(env_classes) > 1:
            class_names = [cls.__name__ for cls in env_classes]
            raise ValueError(f"Multiple environment factory classes found: {class_names}\n"
                             f"Please ensure only one factory class per module.")

        return env_classes[0]


class AutoEnvironment:
    """
    Convenient class for loading environment instances in one step.
    
    This is a simplified API for single-use scenarios. For batch operations
    (creating multiple environments from the same repository), use AutoEnvironmentFactory.
    
    Example:
        >>> # Load from HuggingFace
        >>> env = AutoEnvironment.from_repo(
        ...     "swe-bench",
        ...     environment_id="django__django-12345",
        ...     source="hf",
        ...     dataset="princeton-nlp/SWE-bench",
        ...     split="test"
        ... )
        >>> 
        >>> # Load from OSS
        >>> env = AutoEnvironment.from_repo(
        ...     "swe-bench",
        ...     environment_id="django__django-12345",
        ...     source="oss",
        ...     dataset="princeton-nlp/SWE-bench",
        ...     split="test",
        ...     oss_region="cn-hangzhou",
        ...     oss_endpoint="oss-cn-hangzhou.aliyuncs.com",
        ...     oss_access_key_id="...",
        ...     oss_access_key_secret="..."
        ... )
        >>> 
        >>> # Create task
        >>> task = env.create_task(job)
    
    Note:
        For batch operations, use AutoEnvironmentFactory:
        
        >>> factory = AutoEnvironmentFactory.from_repo("swe-bench")
        >>> env1 = factory.get_from_hf("django-123", ...)
        >>> env2 = factory.get_from_hf("flask-456", ...)  # Reuses factory
    """

    @classmethod
    def from_repo(
        cls,
        repo_name_or_path: Union[str, Path],
        environment_id: str,
        source: str,
        revision: Optional[str] = None,
        username: Optional[str] = None,
        token: Optional[str] = None,
        force_reload: bool = False,
        **kwargs: Any,
    ) -> BaseEnvironment:
        """
        Load an environment instance from repository configuration with specified data source.
        
        This method combines two steps:
        1. Load environment factory from repository (configuration)
        2. Get environment instance from data source (HF/OSS/etc.)
        
        Args:
            repo_name_or_path: Repository name or path for environment configuration
                              (e.g., "swe-bench", "ix-hub/swe-bench", "./my-env")
            environment_id: Unique environment/instance identifier
            source: Data source type ("hf", "oss", or custom)
            revision: Repository revision for configuration. Default: None.
                     If None, automatically resolves to the latest commit hash of the default branch.
            username: Username for private repository authentication
            token: Token/password for private repository authentication
            force_reload: If True, re-download even if cached. Only applies to repository configuration.
            **kwargs: Data source specific parameters:
                     - For "hf": dataset, split, token (optional), revision (optional)
                     - For "oss": dataset, split, oss_region, oss_endpoint, 
                                 oss_access_key_id, oss_access_key_secret, revision (optional)
        
        Returns:
            Loaded environment instance.
        
        Example (HuggingFace):
            >>> env = AutoEnvironment.from_repo(
            ...     repo_name_or_path="swe-bench",
            ...     environment_id="django__django-12345",
            ...     source="hf",
            ...     dataset="princeton-nlp/SWE-bench",
            ...     split="test"
            ... )
        
        Example (Latest version with force reload):
            >>> env = AutoEnvironment.from_repo(
            ...     repo_name_or_path="ix-hub/swe-bench",
            ...     environment_id="django__django-12345",
            ...     source="hf",
            ...     dataset="princeton-nlp/SWE-bench",
            ...     split="test",
            ...     force_reload=True
            ... )
        
        Example (Private Repository):
            >>> env = AutoEnvironment.from_repo(
            ...     repo_name_or_path="company/private-bench",
            ...     environment_id="task-123",
            ...     source="hf",
            ...     dataset="company/dataset",
            ...     split="test",
            ...     username="user",
            ...     token="ghp_xxxxx"
            ... )
        
        Example (OSS):
            >>> env = AutoEnvironment.from_repo(
            ...     repo_name_or_path="swe-bench",
            ...     environment_id="django__django-12345",
            ...     source="oss",
            ...     dataset="princeton-nlp/SWE-bench",
            ...     split="test",
            ...     oss_region="cn-hangzhou",
            ...     oss_endpoint="oss-cn-hangzhou.aliyuncs.com",
            ...     oss_access_key_id="your-key-id",
            ...     oss_access_key_secret="your-secret-key"
            ... )
        
        Note:
            The repo_name_or_path refers to the environment configuration repository,
            while source/kwargs specify where to load the actual environment data from.
        """
        # Step 1: Load factory from repository (configuration) with authentication
        factory = AutoEnvironmentFactory.from_repo(repo_name_or_path, revision, username, token, force_reload)

        # Step 2: Get instance from data source
        if source == "hf":
            return factory.get_from_hf(environment_id, **kwargs)
        elif source == "oss":
            return factory.get_from_oss(environment_id, **kwargs)
        else:
            raise ValueError(f"Unsupported environment source: {source}")


class AutoWorkflow:
    """
    Auto class for loading workflows from repositories.
    
    Similar to AutoScaffold and AutoEnvironmentFactory, this class automatically:
    1. Loads the module from the specified repository and revision
    2. Discovers the workflow class in the module
    3. Loads configuration using from_repo()
    4. Returns an instantiated workflow
    
    Example:
        >>> # Load builtin workflow (no "/" in path)
        >>> workflow_template = AutoWorkflow.from_repo("rollout-and-verify")
        >>> 
        >>> # Load from remote/local repository (contains "/")
        >>> workflow_template = AutoWorkflow.from_repo("ix-hub/custom-workflow", revision="v2.0")
        >>> 
        >>> # Create workflow
        >>> workflow = workflow_template.create_workflow(
        ...     name="run-001",
        ...     agent=agent,
        ...     environment=env,
        ...     agent_context=context,
        ... )
        >>> 
        >>> # Submit to Argo
        >>> workflow.create()
    
    Note:
        For better IDE support (method navigation, autocomplete), you can add type hints:
        
        >>> from interaxions.workflows.rollout_and_verify import RolloutAndVerify
        >>> workflow: RolloutAndVerify = AutoWorkflow.from_repo("rollout-and-verify")
        >>> # Now IDE can navigate to RolloutAndVerify methods
    """

    @classmethod
    def from_repo(
        cls,
        repo_name_or_path: Union[str, Path],
        revision: Optional[str] = None,
        username: Optional[str] = None,
        token: Optional[str] = None,
        force_reload: bool = False,
    ) -> BaseWorkflow:
        """
        Load a workflow from a repository with optional authentication for private repos.
        
        The loading priority:
        1. Try builtin (interaxions.workflows.*)
        2. Use dynamic loading (remote/local repository)
        
        Args:
            repo_name_or_path: Repository name or path.
                      - Builtin: "rollout-and-verify" (no "/" → interaxions.workflows.rollout_and_verify)
                      - Dynamic: "ix-hub/custom-workflow" (has "/" → dynamic load)
                      - Local: "./my-workflow" or Path("./my-workflow")
            revision: Git revision (branch, tag, or commit). Default: None.
                     If None, automatically resolves to the latest commit hash of the default branch.
                     Only used for dynamic loading (ignored for builtin).
            username: Username for private repository authentication
            token: Token/password for private repository authentication
            force_reload: If True, re-download even if cached. Only applies to remote/local repositories.
        
        Returns:
            Workflow instance.
        
        Example:
            >>> # Builtin
            >>> wf = AutoWorkflow.from_repo("rollout-and-verify")
            >>> 
            >>> # Dynamic loading (latest commit)
            >>> wf = AutoWorkflow.from_repo("username/custom-workflow")
            >>> 
            >>> # Specific version
            >>> wf = AutoWorkflow.from_repo("username/custom-workflow", revision="v1.0")
            >>> 
            >>> # Force reload to get updates
            >>> wf = AutoWorkflow.from_repo("username/custom-workflow", force_reload=True)
            >>> 
            >>> # Private repository
            >>> wf = AutoWorkflow.from_repo(
            ...     "company/private-workflow",
            ...     username="user",
            ...     token="ghp_xxxxx"
            ... )
        """
        # Check if it's a builtin workflow
        # Builtin: no "/" or "." or "~" → try interaxions.workflows.*
        repo_path_str = str(repo_name_or_path)
        if not any(char in repo_path_str for char in ['/', '.', '~']):
            try:
                return cls._load_builtin_workflow(repo_path_str)
            except ImportError as e:
                logger.debug(f"Not a builtin workflow: {e}")
                # Fall through to dynamic loading

        # Dynamic loading (remote/local) with authentication support
        return cls._load_dynamic_workflow(repo_path_str, revision, username, token, force_reload)

    @classmethod
    def _load_builtin_workflow(cls, name: str) -> BaseWorkflow:
        """
        Load a builtin workflow from interaxions.workflows.
        
        Args:
            name: Workflow name (e.g., "rollout-and-verify")
            
        Returns:
            Workflow instance with default configuration.
            
        Raises:
            ImportError: If builtin workflow not found.
        """
        # Skip if it looks like a path (contains /, ., or ~)
        if any(char in name for char in ['/', '.', '~']):
            raise ImportError(f"'{name}' looks like a path, not a builtin workflow name")

        # Convert name to module name (rollout-and-verify -> rollout_and_verify)
        module_name = name.replace("-", "_")

        # Try to import the builtin module (will raise ImportError if not found)
        module = importlib.import_module(f"interaxions.workflows.{module_name}")

        # Find workflow class
        workflow_class = cls._discover_workflow_class(module)

        logger.info(f"Loaded builtin workflow: {workflow_class.__name__}")

        # Create instance with default config
        # Builtin workflows should have all config fields with defaults
        from interaxions.workflows.base_workflow import BaseWorkflowConfig
        config_class = getattr(workflow_class, "config_class", BaseWorkflowConfig)
        config = config_class(type=name)

        return workflow_class(config=config)

    @classmethod
    def _load_dynamic_workflow(
        cls,
        repo_name_or_path: str,
        revision: str,
        username: Optional[str] = None,
        token: Optional[str] = None,
        force_reload: bool = False,
    ) -> BaseWorkflow:
        """
        Load a workflow from a remote or local repository with optional authentication.
        
        Args:
            repo_name_or_path: Repository name or path (e.g., "ix-hub/custom-workflow" or "./my-workflow")
            revision: Git revision
            username: Username for private repository authentication
            token: Token/password for private repository authentication
            force_reload: If True, re-download even if cached
            
        Returns:
            Workflow instance loaded from repository.
        """
        hub_manager = get_hub_manager()

        # Get the module path (handles caching and checkout) with authentication
        module_path = hub_manager.get_module_path(
            repo_name_or_path, revision, force_reload=force_reload, username=username, token=token
        )

        logger.info(f"Loading workflow from {repo_name_or_path}@{revision}")
        logger.info(f"Module path: {module_path}")

        # Load the Python module dynamically
        workflow_module = hub_manager.load_module(repo_name_or_path, "workflow", revision, force_reload=force_reload)

        # Discover the workflow class
        workflow_class = cls._discover_workflow_class(workflow_module)

        logger.info(f"Using workflow class: {workflow_class.__name__}")

        # Load workflow using from_repo()
        workflow = workflow_class.from_repo(module_path)

        logger.info(f"Successfully loaded workflow: {workflow_class.__name__}")
        return workflow

    @staticmethod
    def _discover_workflow_class(module: Any) -> type:
        """
        Auto-discover the workflow class in a module.
        
        Looks for classes that inherit from BaseWorkflow.
        
        Args:
            module: Python module object.
            
        Returns:
            Workflow class.
            
        Raises:
            ValueError: If no workflow class found or multiple found.
        """
        import inspect
        from interaxions.workflows.base_workflow import BaseWorkflow

        workflow_classes = []
        for name, obj in inspect.getmembers(module):
            if (inspect.isclass(obj) and issubclass(obj, BaseWorkflow) and obj is not BaseWorkflow):
                workflow_classes.append(obj)

        if len(workflow_classes) == 0:
            raise ValueError(f"No workflow class found in module.\n"
                             f"Expected a class inheriting from BaseWorkflow.\n"
                             f"Available classes: {[name for name, obj in inspect.getmembers(module) if inspect.isclass(obj)]}")

        if len(workflow_classes) > 1:
            class_names = [cls.__name__ for cls in workflow_classes]
            raise ValueError(f"Multiple workflow classes found: {class_names}\n"
                             f"Please ensure only one workflow class per module.")

        return workflow_classes[0]
