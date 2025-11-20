# puck_build/models/workspace.py
#
# Puck - Build Manager for Modular C++-Projects
#
# Copyright (c) 2025 Florian Giesemann
# This file is distributed under the terms of the MIT License

"""
Defines the workspace model class which represent a main project that contains
subprojects in their separate directories and repositories.
"""

from pathlib import Path
from typing import List, Dict, Any, Set, Tuple
import json
from enum import Enum

from puck_build.models.project import (
    REQUIRED_PROJECT_KEYS,
    OPTIONAL_DEFAULTS_KEYS,
    OPTIONAL_KEYS,
    Project,
)


class WorkspaceNotFoundError(Exception):
    pass


class InvalidWorkspaceConfigError(ValueError):
    pass


class GraphState(Enum):
    """
    Defines the states used during the Depth-First Search (DFS)
    for topological sorting and cycle detection.
    """

    UNVISITED = 0
    VISITING = 1
    VISITED = 2


class Workspace:
    """
    Search and load the puck-workspace.json file. The location of that file
    defines the workspace root directory.
    """

    CONFIG_FILE_NAME = "puck-workspace.json"
    LOCAL_SETTINGS_FILE_NAME = ".puck-local.json"

    def __init__(self, start_dir: Path) -> None:
        """
        Initializes the workspace. Searches for the workspace configuration file
        beginning from the given directory.

        Args:
            start_dir (Path): The directory to start the search from.
        """
        self._workspace_root: Path = self._find_workspace_root(start_dir)
        self.raw_config = self._load_config_file()
        self._validate_config()
        self.local_settings: Dict[str, Any] = self._load_local_settings()
        self.projects: List[Project] = self._process_projects()
        self.sorted_projects: List[Project]
        self.project_map: Dict[str, Project]
        self.sorted_projects, self.project_map = self._analyze_and_sort_graph()

    @property
    def workspace_root(self) -> Path:
        return self._workspace_root

    @property
    def workspace_config_path(self) -> Path:
        """Der absolute Pfad zur puck-workspace.json Datei."""
        return self.workspace_root / self.CONFIG_FILE_NAME

    @property
    def local_settings_path(self) -> Path:
        """Der absolute Pfad zur .puck-local.json Datei."""
        return self.workspace_root / self.LOCAL_SETTINGS_FILE_NAME

    def _find_workspace_root(self, start_dir: Path) -> Path:
        current_dir = start_dir.resolve()
        while True:
            config_file_path = current_dir / self.CONFIG_FILE_NAME
            if config_file_path.is_file():
                return current_dir
            if current_dir.parent == current_dir:
                raise WorkspaceNotFoundError(
                    f"Could not find workspace configuration file. Searched from {start_dir}"
                )
            current_dir = current_dir.parent

    def _load_config_file(self) -> dict:
        try:
            with self.workspace_config_path.open(encoding="utf-8") as f:
                data = json.load(f)
                return data

        except FileNotFoundError:
            raise WorkspaceNotFoundError(
                f"Could not find workspace configuration file. Expected it at '{self.workspace_config_path}'."
            )

        except json.JSONDecodeError as e:
            raise ValueError(
                f"Error reading workspace configration file '{self.workspace_config_path}': "
                f"Invalid JSON: {e}"
            )

    def _load_local_settings(self) -> Dict[str, Any]:
        """
        Loads local, non-version-controlled settings from .puck-local.json.

        Returns:
            The loaded dictionary or an empty dictionary if the file does not exist.
        Raises:
            IOError: If the file exists but is unreadable or malformed JSON.
        """
        local_settings_path = self.local_settings_path

        if not local_settings_path.exists():
            return {}

        try:
            with open(local_settings_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            raise IOError(
                f"Local settings file found at '{local_settings_path}' is not valid JSON: {e}"
            )
        except IOError as e:
            raise IOError(
                f"Could not read local settings file at '{local_settings_path}': {e}"
            )

    def _process_projects(self) -> List[Project]:
        """
        Instantiates Project objects from the raw configuration list.

        Note: This only does object creation. Semantic validation (e.g., dependency cycles)
        must be performed after this step.
        """
        projects_list: List[Dict[str, Any]] = self.raw_config["projects"]
        project_instances: List[Project] = []

        for project_data in projects_list:
            project = Project(project_data, self.workspace_root)
            project_instances.append(project)

        return project_instances

    def _analyze_and_sort_graph(self) -> Tuple[List[Project], Dict[str, Project]]:
        """
        Analyzes the dependency graph:
        1. Checks for unknown project names (duplicates).
        2. Checks for unknown dependencies.
        3. Performs a topological sort and checks for dependency cycles.

        Returns:
            A tuple: (sorted_projects_list, project_name_to_object_map)

        Raises:
            InvalidWorkspaceConfigError: On unknown dependencies or cycles.
        """
        project_name_map: Dict[str, Project] = {}
        for project in self.projects:
            if project.name in project_name_map:
                raise InvalidWorkspaceConfigError(
                    f"Duplicate project name found: '{project.name}'. Project names must be unique."
                )
            project_name_map[project.name] = project
        available_names: Set[str] = set(project_name_map.keys())

        sorted_list: List[Project] = []
        visited_state: Dict[str, GraphState] = {
            name: GraphState.UNVISITED for name in available_names
        }

        def _dfs_sort(project_name: str, path: List[str]):
            """Recursive DFS helper for sorting and cycle detection."""

            if project_name not in project_name_map:
                chain = " -> ".join(path)
                raise InvalidWorkspaceConfigError(
                    f"Unknown dependency '{project_name}'. "
                    f"The project is required by: {chain}."
                )

            project = project_name_map[project_name]

            state = visited_state[project_name]
            if state == GraphState.VISITING:
                cycle_index = path.index(project_name)
                cycle = " -> ".join(path[cycle_index:] + [project_name])
                raise InvalidWorkspaceConfigError(
                    f"Dependency cycle detected: {cycle}."
                )

            if state == GraphState.VISITED:
                return

            visited_state[project_name] = GraphState.VISITING
            path.append(project_name)

            for dep_name in project.depends_on:
                _dfs_sort(dep_name, path)

            visited_state[project_name] = GraphState.VISITED

            sorted_list.append(project)
            path.pop()

        for name in available_names:
            if visited_state[name] == GraphState.UNVISITED:
                _dfs_sort(name, [])

        return list(reversed(sorted_list)), project_name_map

    def _validate_config(self):
        """
        Performs basic structural validation on the raw configuration data.

        Raises:
            InvalidWorkspaceConfigError: If the structure is invalid.
        """
        if "projects" not in self.raw_config:
            raise InvalidWorkspaceConfigError(
                "Top-level key 'projects' is missing from the configuration."
            )
        projects_list = self.raw_config["projects"]

        if not isinstance(projects_list, list):
            raise InvalidWorkspaceConfigError(
                f"Expected 'projects' to be a list, but found type {type(projects_list).__name__}."
            )

        for i, project_data in enumerate(projects_list):
            for key in REQUIRED_PROJECT_KEYS:
                if key not in project_data:
                    raise InvalidWorkspaceConfigError(
                        f"Project at index {i} is missing the required key '{key}'."
                    )

            if "depends_on" in project_data and not isinstance(
                project_data["depends_on"], list
            ):
                raise InvalidWorkspaceConfigError(
                    f"Project '{project_data['name']}' requires 'depends_on' to be a list if specified."
                )

            allowed_keys = (
                set(REQUIRED_PROJECT_KEYS)
                | set(OPTIONAL_KEYS)
                | set(OPTIONAL_DEFAULTS_KEYS.keys())
            )
            for key in project_data.keys():
                if key not in allowed_keys:
                    print(
                        f"Warning: Project '{project_data['name']}' contains unknown key '{key}'. Ignoring."
                    )
