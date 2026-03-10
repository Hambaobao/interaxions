"""
Shared base configuration class for all ix-hub repo configs.

All *Config classes (BaseScaffoldConfig, BaseEnvironmentConfig,
BaseWorkflowConfig, BaseTaskConfig, ...) inherit from BaseRepoConfig
to share the YAML loading and template-expansion logic.
"""

from pathlib import Path
from typing import Any, Dict, Type, TypeVar, Union

import yaml

from pydantic import BaseModel


TBaseRepoConfig = TypeVar("TBaseRepoConfig", bound="BaseRepoConfig")


class BaseRepoConfig(BaseModel):
    """
    Mixin that provides config.yaml loading and Jinja2 template expansion
    for all ix-hub repository config classes.

    Subclasses must declare their own fields (repo_type, type, image, …).
    They inherit three class-methods for free:

        _load_config_dict  – locate and parse config.yaml / config.yml
        _load_templates    – inline template files referenced in the config
        from_repo          – validate the directory, then load and return an instance

    Subclasses may override from_repo() if they need custom post-processing,
    but _load_config_dict and _load_templates rarely need to change.
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
            raise FileNotFoundError(
                f"Config file not found in {repo_name_or_path}. "
                "Expected 'config.yaml' or 'config.yml'."
            )
        with open(config_file, "r", encoding="utf-8") as f:
            config_dict = yaml.safe_load(f)
        if not isinstance(config_dict, dict):
            raise ValueError(
                f"Invalid config file: {config_file}. Expected a YAML mapping, "
                f"got {type(config_dict).__name__}."
            )
        return config_dict

    @classmethod
    def _load_templates(
        cls, config_dict: Dict[str, Any], repo_name_or_path: Union[str, Path]
    ) -> Dict[str, Any]:
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
                raise ValueError(
                    f"Template '{name}' must be a file path string, "
                    f"got {type(path).__name__}."
                )
            template_file = Path(repo_name_or_path) / path
            if not template_file.exists():
                raise FileNotFoundError(
                    f"Template file not found: {template_file}\n"
                    f"Template '{name}' references '{path}' which does not exist."
                )
            with open(template_file, "r", encoding="utf-8") as f:
                loaded[name] = f.read()

        config_dict["templates"] = loaded
        return config_dict

    @classmethod
    def from_repo(
        cls: Type[TBaseRepoConfig], repo_name_or_path: Union[str, Path]
    ) -> TBaseRepoConfig:
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

