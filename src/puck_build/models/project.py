# puck_build/models/project.py
#
# Puck - Build Manager for Modular C++-Projects
#
# Copyright (c) 2025 Florian Giesemann
# This file is distributed under the terms of the MIT License

"""
Defines the project model class that describes a subproject in a workspace.
"""

from pathlib import Path
from typing import List, Dict, Any, Union, Callable

REQUIRED_PROJECT_KEYS: List[str] = ["name"]
OPTIONAL_DEFAULTS_KEYS: Dict[str, Union[Any, Callable[[str], str]]] = {
    "path": lambda name: name,
    "depends_on": [],
}
OPTIONAL_KEYS: List[str] = ["repository_url"]


class Project:
    """
    Represents a single project definition loaded from the puck-workspace.json.
    Handles applying default values for optional fields and calculating absolute paths.
    """

    def __init__(self, raw_data: Dict[str, Any], workspace_root: Path):
        """
        Initializes a Project instance.

        Assumes raw_data has passed the structural validation in Workspace._validate_config.

        Args:
            raw_data: The dictionary data for this project from the configuration file.
            workspace_root: The absolute path to the root of the workspace.
        """
        self._name: str = raw_data["name"]
        path_default_func = OPTIONAL_DEFAULTS_KEYS["path"]
        self._path: str = raw_data.get(
            "path",
            path_default_func(self._name)
            if callable(path_default_func)
            else path_default_func,
        )
        self._absolute_path: Path = workspace_root / self._path
        self._repository_url: str | None = raw_data.get("repository_url", None)
        self._depends_on: List[str] = raw_data.get(
            "depends_on", OPTIONAL_DEFAULTS_KEYS["depends_on"]
        )

    @property
    def name(self) -> str:
        return self._name

    @property
    def path(self) -> str:
        return self._path

    @property
    def absolute_path(self) -> Path:
        """The absolute path to the project's root directory."""
        return self._absolute_path

    @property
    def repository_url(self) -> str | None:
        return self._repository_url

    @property
    def depends_on(self) -> List[str]:
        return self._depends_on

    def __repr__(self) -> str:
        return f"Project(name='{self.name}', path='{self.path}')"
