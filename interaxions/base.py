"""
Shared base classes for all ix-hub repositories.

Two classes are provided:

    BaseRepoConfig  – Pydantic base for config.yaml models.
                      Handles YAML loading and Jinja2 template file expansion.
                      Subclass it to define repo-specific config fields.

    BaseRepo        – ABC base for runtime executor objects (scaffolds,
                      environments, tasks, workflows).
                      Provides __init__, from_repo, and render_template so
                      subclasses only need to implement their domain logic.
"""

from abc import ABC
from pathlib import Path
from typing import Any, Dict, Type, TypeVar, Union

import yaml

from jinja2 import Template
from pydantic import BaseModel

# ---------------------------------------------------------------------------
# Config base
# ---------------------------------------------------------------------------

TBaseRepoConfig = TypeVar("TBaseRepoConfig", bound="BaseRepoConfig")


class BaseRepoConfig(BaseModel):
    """
    Pydantic base for all ix-hub repository config classes.

    Subclasses declare their own fields (``repo_type``, ``image``,
    ``templates``, …).  Three class-methods are provided so subclasses never
    need to repeat YAML-loading boilerplate:

        _load_config_dict  – locate and parse config.yaml / config.yml
        _load_templates    – inline template files referenced in the config
        from_repo          – validate the directory, load, expand, and return
                             an instance of the calling config class
    """

    @classmethod
    def _load_config_dict(cls, repo_name_or_path: Union[str, Path]) -> Dict[str, Any]:
        """
        Locate and parse config.yaml (or config.yml) from the repo directory.

        Args:
            repo_name_or_path: Path to the repository directory.

        Returns:
            Parsed configuration dictionary.

        Raises:
            FileNotFoundError: If neither config.yaml nor config.yml exists.
            ValueError: If the file is empty or does not parse to a dict.
        """
        config_file = Path(repo_name_or_path) / "config.yaml"
        if not config_file.exists():
            config_file = Path(repo_name_or_path) / "config.yml"
        if not config_file.exists():
            raise FileNotFoundError(f"Config file not found in {repo_name_or_path}. "
                                    "Expected 'config.yaml' or 'config.yml'.")
        with open(config_file, "r", encoding="utf-8") as f:
            config_dict = yaml.safe_load(f)
        if not isinstance(config_dict, dict):
            raise ValueError(f"Invalid config file: {config_file}. Expected a YAML mapping, "
                             f"got {type(config_dict).__name__}.")
        return config_dict

    @classmethod
    def _load_templates(cls, config_dict: Dict[str, Any], repo_name_or_path: Union[str, Path]) -> Dict[str, Any]:
        """
        Inline template files referenced under the ``templates`` key.

        Each value in ``config.templates`` must be a relative file path
        (e.g. ``"templates/main.j2"``). The file is read and its content
        replaces the path string in the returned dict.

        Args:
            config_dict: Parsed configuration dictionary (mutated in-place).
            repo_name_or_path: Repository root used to resolve relative paths.

        Returns:
            The same config_dict with template paths replaced by file contents.

        Raises:
            ValueError: If a template value is not a string path.
            FileNotFoundError: If a referenced template file does not exist.
        """
        if "templates" not in config_dict or not isinstance(config_dict["templates"], dict):
            return config_dict

        loaded: Dict[str, str] = {}
        for name, path in config_dict["templates"].items():
            if not isinstance(path, str):
                raise ValueError(f"Template '{name}' must be a file path string, "
                                 f"got {type(path).__name__}.")
            template_file = Path(repo_name_or_path) / path
            if not template_file.exists():
                raise FileNotFoundError(f"Template file not found: {template_file}\n"
                                        f"Template '{name}' references '{path}' which does not exist.")
            with open(template_file, "r", encoding="utf-8") as f:
                loaded[name] = f.read()

        config_dict["templates"] = loaded
        return config_dict

    @classmethod
    def from_repo(cls: Type[TBaseRepoConfig], repo_name_or_path: Union[str, Path]) -> TBaseRepoConfig:
        """
        Validate the directory, load config.yaml, expand templates, and
        return an instance of the concrete config class.

        Args:
            repo_name_or_path: Path to the repository directory.

        Returns:
            Populated instance of the calling config class.

        Raises:
            FileNotFoundError: If the directory or config file does not exist.
            ValueError: If the path is not a directory or the config is invalid.
        """
        repo_path = Path(repo_name_or_path)
        if not repo_path.exists():
            raise FileNotFoundError(f"Directory not found: {repo_path}")
        if not repo_path.is_dir():
            raise ValueError(f"Path must be a directory: {repo_path}")

        config_dict = cls._load_config_dict(repo_path)
        config_dict = cls._load_templates(config_dict, repo_path)
        return cls(**config_dict)


# ---------------------------------------------------------------------------
# Runtime object base
# ---------------------------------------------------------------------------

T = TypeVar("T", bound="BaseRepo")


class BaseRepo(ABC):
    """
    Abstract base for all ix-hub runtime objects loaded from a repository.

    Provides three concrete methods that are identical across every executor
    class (scaffold, environment, task, workflow), so subclasses only need to
    declare their config type and implement their domain-specific abstract
    methods.

    Class attributes (override in each subclass):
        config_class: The concrete BaseRepoConfig subclass for this object.

    Instance attributes:
        config: The loaded configuration instance.

    Methods provided:
        __init__        – store the config
        from_repo       – classmethod: load config from a repo directory and
                          return a fully initialised instance
        render_template – render a named Jinja2 template stored in config.templates
    """

    config_class: Type[BaseRepoConfig] = BaseRepoConfig
    config: BaseRepoConfig

    def __init__(self, config: BaseRepoConfig) -> None:
        self.config = config

    @classmethod
    def from_repo(cls: Type[T], repo_name_or_path: Union[str, Path]) -> T:
        """
        Load configuration from a repository directory and return an instance.

        Delegates directory validation and YAML parsing to
        ``config_class.from_repo()``, then constructs ``cls(config=...)``.

        Args:
            repo_name_or_path: Path to a local directory that contains
                               ``config.yaml`` (or ``config.yml``).

        Returns:
            A fully initialised instance of the calling class.

        Raises:
            FileNotFoundError: If the directory or config file does not exist.
            ValueError: If the path is not a directory or the config is invalid.

        Example:
            >>> scaffold = MySWEAgent.from_repo("./swe-agent-repo")
            >>> workflow = RolloutAndVerify.from_repo("./rollout-workflow")
        """
        config = cls.config_class.from_repo(repo_name_or_path)
        return cls(config=config)

    def render_template(self, template_name: str, context: Dict[str, Any]) -> str:
        """
        Render a named Jinja2 template stored in ``config.templates``.

        Templates are loaded from files by ``BaseRepoConfig.from_repo()`` and
        stored as plain strings under ``config.templates``.  Call this method
        after the object has been created via ``from_repo()``.

        Args:
            template_name: Key in ``config.templates`` (e.g. ``"main"``).
            context: Variables to pass to the Jinja2 template.

        Returns:
            Rendered string.

        Raises:
            ValueError: If ``config.templates`` is absent/empty, or the
                        requested template name is not found.

        Example:
            script = self.render_template("main", {
                "instance_id": environment.id,
                "problem_statement": environment.data["problem_statement"],
            })
        """
        if not hasattr(self.config, "templates") or not self.config.templates:
            raise ValueError(f"No templates found in {type(self).__name__} config. "
                             "The object must be loaded via from_repo() to use templates.")
        if template_name not in self.config.templates:
            available = list(self.config.templates.keys())
            raise ValueError(f"Template '{template_name}' not found in {type(self).__name__} config. "
                             f"Available templates: {available}")
        return Template(self.config.templates[template_name]).render(context)
