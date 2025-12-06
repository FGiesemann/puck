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
from typing import List


class Project:
    """
    Represents a single project definition loaded from the puck-workspace.json.
    Handles applying default values for optional fields and calculating absolute paths.
    """

    def __init__(
        self,
        name: str,
        path: Path,
        repository_url: str | None,
        depends_on: List[str] = [],
        conan_editable: bool | None = False,
        no_code: bool | None = False,
    ):
        """
        Initializes a Project instance.
        """
        self._name = name
        self._path = path
        self._repository_url = repository_url
        self._depends_on = depends_on
        self._conan_editable = conan_editable if conan_editable else False
        self._no_code = no_code if no_code else False

        self._absolute_path = self.path.resolve()

    @property
    def name(self) -> str:
        return self._name

    @property
    def path(self) -> Path:
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

    @property
    def conan_editable(self) -> bool:
        return self._conan_editable

    @property
    def no_code(self) -> bool:
        return self._no_code

    def __repr__(self) -> str:
        return f"Project(name='{self.name}', path='{self.path}')"
