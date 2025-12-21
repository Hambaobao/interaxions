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
from typing import Any

from interaxions.hub.hub_manager import get_hub_manager
from interaxions.agents.base_agent import BaseAgent
from interaxions.environments.base_environment import BaseEnvironmentFactory

logger = logging.getLogger(__name__)


class AutoAgent:
    """
    Auto class for loading agents from repositories.
    
    Similar to transformers.AutoModel, this class automatically:
    1. Loads the module from the specified repository and revision
    2. Discovers the agent class in the module
    3. Loads configuration using from_repo()
    4. Returns an instantiated agent
    
    Example:
        >>> # Load builtin agent (no "/" in path)
        >>> agent = AutoAgent.from_repo("swe-agent")
        >>> 
        >>> # Load from remote/local repository (contains "/")
        >>> agent = AutoAgent.from_repo("ix-hub/swe-agent", revision="v1.0.0")
        >>> 
        >>> # Use the agent
        >>> task = agent.create_task(name="task", context=context)
    """

    @classmethod
    def from_repo(cls, repo_path: str, revision: str = "main") -> BaseAgent:
        """
        Load an agent from a repository.
        
        The loading priority:
        1. Try builtin (interaxions.agents.*)
        2. If not builtin, use dynamic loading (remote/local)
        
        Args:
            repo_path: Repository path. Examples:
                - "swe-agent" (builtin agent from interaxions.agents.swe_agent)
                - "my-agent" (local repo or remote if builtin not found)
                - "ix-hub/swe-agent" (remote/local repository)
                - "./my-agent" (local path)
            revision: Git revision (tag, branch, or commit hash). Default: "main".
                Only used for remote/local repositories (ignored for builtin).
            
        Returns:
            Loaded agent instance.
            
        Example:
            >>> # Load builtin agent
            >>> agent = AutoAgent.from_repo("swe-agent")
            >>> 
            >>> # Load from remote repository
            >>> agent = AutoAgent.from_repo("ix-hub/swe-agent", revision="v1.0.0")
            >>> 
            >>> # Load from local path
            >>> agent = AutoAgent.from_repo("my-custom-agent")
        """
        # Try builtin first
        try:
            return cls._load_builtin_agent(repo_path)
        except ImportError:
            # Not builtin, use dynamic loading
            pass

        # Dynamic loading (remote/local)
        return cls._load_dynamic_agent(repo_path, revision)

    @classmethod
    def _load_builtin_agent(cls, name: str) -> BaseAgent:
        """
        Load a builtin agent from interaxions.agents.
        
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
        module = importlib.import_module(f"interaxions.agents.{module_name}")

        # Find agent class
        agent_class = cls._discover_agent_class(module)

        logger.info(f"Loaded builtin agent: {agent_class.__name__}")

        # Create instance with default config
        # Builtin agents should have all config fields with defaults
        from interaxions.agents.base_agent import BaseAgentConfig
        config_class = getattr(agent_class, "config_class", BaseAgentConfig)
        config = config_class()

        return agent_class(config=config)

    @classmethod
    def _load_dynamic_agent(cls, repo_path: str, revision: str) -> BaseAgent:
        """
        Load an agent from a remote or local repository.
        
        Args:
            repo_path: Repository path (e.g., "ix-hub/swe-agent" or "./my-agent")
            revision: Git revision
            
        Returns:
            Agent instance loaded from repository.
        """
        hub_manager = get_hub_manager()

        # Get the module path (handles caching and checkout)
        module_path = hub_manager.get_module_path(repo_path, revision)

        logger.info(f"Loading agent from {repo_path}@{revision}")
        logger.info(f"Module path: {module_path}")

        # Load the Python module dynamically
        agent_module = hub_manager.load_module(repo_path, "agent", revision)

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
        
        Looks for classes that inherit from BaseAgent.
        
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
            if (inspect.isclass(obj) and issubclass(obj, BaseAgent) and obj is not BaseAgent):
                agent_classes.append(obj)

        if len(agent_classes) == 0:
            raise ValueError(f"No agent class found in module.\n"
                             f"Expected a class inheriting from BaseAgent.\n"
                             f"Available classes: {[name for name, obj in inspect.getmembers(module) if inspect.isclass(obj)]}")

        if len(agent_classes) > 1:
            class_names = [cls.__name__ for cls in agent_classes]
            raise ValueError(f"Multiple agent classes found: {class_names}\n"
                             f"Please ensure only one agent class per module.")

        return agent_classes[0]


class AutoEnvironmentFactory:
    """
    Auto class for loading environment factories from repositories.
    
    Similar to AutoAgent and transformers.AutoTokenizer.
    
    Example:
        >>> # Load builtin environment (no "/" in path)
        >>> factory = AutoEnvironmentFactory.from_repo("swe-bench")
        >>> 
        >>> # Load from remote/local repository (contains "/")
        >>> factory = AutoEnvironmentFactory.from_repo("ix-hub/swe-bench", revision="v2.0.0")
        >>> 
        >>> # Create environment instances
        >>> env = factory.get_from_hf(environment_id="django__django-12345", ...)
        >>> 
        >>> # Create verification tasks
        >>> task = env.create_task(name="verify", predictions_path="results.json")
    """

    @classmethod
    def from_repo(cls, repo_path: str, revision: str = "main") -> BaseEnvironmentFactory:
        """
        Load an environment factory from a repository.
        
        The loading priority:
        1. Try builtin (interaxions.environments.*)
        2. If not builtin, use dynamic loading (remote/local)
        
        Args:
            repo_path: Repository path. Examples:
                - "swe-bench" (builtin environment from interaxions.environments.swe_bench)
                - "my-benchmark" (local repo or remote if builtin not found)
                - "ix-hub/swe-bench" (remote/local repository)
                - "./my-benchmark" (local path)
            revision: Git revision (tag, branch, or commit hash). Default: "main".
                Only used for remote/local repositories (ignored for builtin).
            
        Returns:
            Loaded environment factory object.
            
        Example:
            >>> # Load builtin environment
            >>> factory = AutoEnvironment.from_repo("swe-bench")
            >>> 
            >>> # Load from remote repository
            >>> factory = AutoEnvironment.from_repo("ix-hub/swe-bench", revision="v2.0.0")
            >>> 
            >>> # Get environment instances
            >>> env = factory.get_from_hf(environment_id="...", dataset="...", split="test")
        """
        # Try builtin first
        try:
            return cls._load_builtin_environment(repo_path)
        except ImportError:
            # Not builtin, use dynamic loading
            pass

        # Dynamic loading (remote/local)
        return cls._load_dynamic_environment(repo_path, revision)

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
    def _load_dynamic_environment(cls, repo_path: str, revision: str) -> BaseEnvironmentFactory:
        """
        Load an environment from a remote or local repository.
        
        Args:
            repo_path: Repository path (e.g., "ix-hub/swe-bench" or "./my-benchmark")
            revision: Git revision
            
        Returns:
            Environment factory instance loaded from repository.
        """
        hub_manager = get_hub_manager()

        # Get the module path (handles caching and checkout)
        module_path = hub_manager.get_module_path(repo_path, revision)

        logger.info(f"Loading environment factory from {repo_path}@{revision}")
        logger.info(f"Module path: {module_path}")

        # Load the Python module dynamically
        env_module = hub_manager.load_module(repo_path, "env", revision)

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
