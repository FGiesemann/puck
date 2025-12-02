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

from dataclasses import asdict
from pathlib import Path
from typing import List, Dict, Any
import json
from enum import Enum

from puck_build.models.config import (
    BuildProfile,
    GlobalConfig,
    LocalBuildConfig,
    ProjectDefinition,
    WorkspaceConfig,
)
from puck_build.models.project import Project
from puck_build.tools.cmake import CMakeTool, CMakeToolError
from puck_build.tools.conan import ConanTool
from puck_build.tools.git import GitTool, GitToolError
from puck_build.utils.config_loader import deserialize_config
from puck_build.utils.logger import LogLevel, logger


class WorkspaceNotFoundError(Exception):
    pass


class InvalidWorkspaceConfigError(ValueError):
    pass


class ExistingPathHandling(Enum):
    """Defines how the setup command handles target directories that already exist."""

    FAIL = "fail"
    SKIP = "skip"
    OVERWRITE = "overwrite"


class VisitState(Enum):
    """States for the nodes during the topological sort (DFS)."""

    UNVISITED = 1  # Node not yet visited
    VISITING = 2  # Node currently in the recursion stack (potential cycle)
    VISITED = 3  # Node and all its dependencies have been processed


class Workspace:
    """
    Search and load the puck-workspace.json file. The location of that file
    defines the workspace root directory.
    """

    WORKSPACE_CONFIG_FILE_NAME = "puck-workspace.json"
    LOCAL_BUILD_CONFIG_FILE_NAME = "puck-build.json"

    def __init__(self, start_dir: Path, dry_run: bool = False) -> None:
        """
        Initializes the workspace. Searches for the workspace configuration file
        beginning from the given directory.

        Args:
            start_dir (Path): The directory to start the search from.
            dry_run (bool): Print commands instead of executing them
        """
        logger.debug(f"[workspace] searching puck workspace from {start_dir}")
        self._workspace_root: Path = self._find_workspace_root(start_dir)
        logger.debug(f"[workspace] workspace root: {self.workspace_root}")
        self._load_configs()
        self.resolved_profiles = self._resolve_build_profiles()
        self._create_projects_from_config()
        self._dry_run = dry_run
        self._sorted_projects = self._topological_sort()

    @property
    def workspace_root(self) -> Path:
        return self._workspace_root

    @property
    def workspace_config_path(self) -> Path:
        return self.workspace_root / self.WORKSPACE_CONFIG_FILE_NAME

    @property
    def local_build_config_path(self) -> Path:
        return self.workspace_root / self.LOCAL_BUILD_CONFIG_FILE_NAME

    @property
    def global_config_path(self) -> Path:
        return Path.home() / ".puck" / "build-config.json"

    @property
    def projects(self) -> List[Project]:
        return self._sorted_projects

    def setup_projects(self, clean: bool = False) -> None:
        """
        Clones or updates all defined sub-projects in the workspace.
        Considers the project path and handles submodules recursively.
        """
        git_tool = GitTool(self._dry_run)
        conan_tool = ConanTool(self._dry_run)

        for p_def in self.workspace_config.projects:
            project_name = p_def.name
            repository_url = p_def.repository_url

            if not repository_url:
                logger.warning(
                    f"Project '{project_name}' has no 'repository_url'. Skipping setup."
                )
                continue

            project_dir_name = p_def.path if p_def.path else p_def.name
            target_dir = self.workspace_root / project_dir_name

            logger.info(
                f"Setting up project: **{project_name}** at {target_dir.relative_to(self.workspace_root)}"
            )

            try:
                if target_dir.exists():
                    if clean:
                        git_tool.clean_repo(repo_dir=target_dir)
                        logger.info(
                            f"  SUCCESS: Aggressively reset and cleaned {project_name}."
                        )
                    else:
                        logger.debug("Directory exists, updating repository...")
                        git_tool.update_repo(repo_dir=target_dir)
                        logger.info(f"  SUCCESS: Updated {project_name}.")
                else:
                    logger.debug("Directory does not exist, cloning repository...")
                    target_dir.parent.mkdir(parents=True, exist_ok=True)
                    git_tool.clone_repo(url=repository_url, target_dir=target_dir)
                    logger.info(f"  SUCCESS: Cloned {project_name}.")
            except GitToolError as e:
                logger.error(f"Critical Git error during setup for {project_name}: {e}")
                raise RuntimeError("Setup process aborted due to Git error.")
        self._ensure_editable_packages_added(conan_tool)

    def install_projects(self, profile_names: List[str]) -> None:
        """
        Executes 'conan install' for all projects in the correct build order,
        using the specified profiles.
        """
        conan_tool = ConanTool(self._dry_run)
        self._ensure_editable_packages_added(conan_tool)
        for project in self.projects:
            logger.info(f"Installing dependencies for project: **{project.name}**")
            for profile_name in profile_names:
                profile = self.resolved_profiles.get(profile_name)

                if not profile:
                    raise ValueError(f"Profile '{profile_name}' not found or resolved.")

                logger.debug(f"  Using build profile: {profile_name}")
                try:
                    # target folder (--output-folder) will only be used, when the user defines it explicitly in the project configuration.
                    # Otherwise, the default build folder as dictated by the conan profile/settings will be used
                    install_folder = profile.build_directory

                    conan_tool.install(
                        project_path=project.path,
                        conan_profile_name=profile.conan.profile_name,
                        settings=profile.conan.settings,
                        install_folder=install_folder,
                        # TODO: Add e.g., --build=missing
                    )
                    logger.info(
                        f"  SUCCESS: Conan install finished for {project.name} ({profile_name})."
                    )

                except Exception as e:
                    logger.error(
                        f"Critical error during Conan install for {project.name} ({profile_name}): {e}"
                    )
                    raise RuntimeError("Installation process aborted.")

    def build_projects(self, profile_names: List[str], target: str) -> None:
        """
        Executes 'cmake --build' for all projects in the correct build order,
        using the specified profiles and target.
        """
        cmake_tool = CMakeTool(self._dry_run)

        for project in self.projects:
            logger.info(f"Building project: **{project.name}**")

            for profile_name in profile_names:
                profile = self.resolved_profiles.get(profile_name)

                if not profile:
                    raise ValueError(f"Profile '{profile_name}' not found or resolved.")

                logger.debug(f"  Using build profile: {profile_name}")

                preset_name = profile.build.config
                explicit_build_dir = profile.build_directory

                build_path_to_use = None
                if preset_name:
                    logger.debug(f"  Build Mode: Preset ('{preset_name}')")
                elif explicit_build_dir:
                    build_path_to_use = explicit_build_dir
                    logger.debug(f"  Build Mode: Directory ('{build_path_to_use}')")
                else:
                    logger.warning(
                        f"Profile '{profile_name}' for project '{project.name}' is incomplete "
                        f"(missing 'build.config' and 'build_directory'). Skipping build."
                    )
                    continue

                try:
                    cmake_tool.configure(
                        project_path=project.path,
                        preset_name=preset_name,
                        build_path=build_path_to_use,
                    )
                    cmake_tool.build(
                        project_path=project.path,
                        preset_name=preset_name,
                        build_path=build_path_to_use,
                        build_target=target,
                    )
                    logger.info(
                        f"  SUCCESS: Build finished for {project.name} ({profile_name})."
                    )

                except CMakeToolError as e:
                    logger.error(
                        f"Critical error during CMake build for {project.name} ({profile_name}): {e}"
                    )
                    raise RuntimeError("Build process aborted.")

    def check_config(self) -> None:
        """
        Analyzes the workspace configuration and prints the resolved state
        (profiles and project build order).
        """
        logger.print("## 1. Resolved Build Profiles")
        if not self.resolved_profiles:
            logger.warning("No build profiles found in local or global configuration.")
        else:
            for name, profile in self.resolved_profiles.items():
                logger.print(f"  - {name}")
                settings_count = len(profile.conan.settings)
                inherits = (
                    profile.inherits_from
                    if hasattr(profile, "inherits_from") and profile.inherits_from
                    else "None"
                )

                logger.print(
                    f"    Settings keys: {settings_count}, Inherits from: {inherits}"
                )
                if logger.min_level.value >= LogLevel.VERBOSE.value:
                    logger.print(f"    [SETTINGS] {dict(profile.conan.settings)}")

        logger.print("\n## 2. Project Build Order")
        if not self.projects:
            logger.warning("No projects defined in workspace configuration.")
        else:
            for i, project in enumerate(self.projects):
                path = project.path
                editable_status = " (EDITABLE)" if project.conan_editable else ""

                logger.print(
                    f"  {i + 1}. {project.name}{editable_status} [Path: {path.relative_to(self.workspace_root)}]"
                )

                if logger.min_level.value >= LogLevel.VERBOSE.value:
                    logger.print(f"     Depends on: {', '.join(project.depends_on)}")

    def _ensure_editable_packages_added(self, conan_tool: ConanTool):
        """
        Ensures that all projects with 'conan_editable: true' in the workspace
        config are added as editable packages to the conan cache.
        """
        for p_def in self.workspace_config.projects:
            if p_def.conan_editable:
                project_path = self._get_project_path(p_def)

                logger.debug(
                    f"Checking editable status for {p_def.name} at {project_path.name}"
                )

                conan_tool.add_editable(project_path=project_path)
                logger.debug(f"Ensured {p_def.name} is added as editable.")

    def _find_workspace_root(self, start_dir: Path) -> Path:
        current_dir = start_dir.resolve()
        while True:
            config_file_path = current_dir / self.WORKSPACE_CONFIG_FILE_NAME
            if config_file_path.is_file():
                return current_dir
            if current_dir.parent == current_dir:
                raise WorkspaceNotFoundError(
                    f"Could not find workspace configuration file. Searched from {start_dir}"
                )
            current_dir = current_dir.parent

    def _load_configs(self) -> None:
        """Loads all configuration files used by puck."""

        logger.debug(f"Loading workspace config from {self.workspace_config_path}")
        workspace_data = self._load_json_file(self.workspace_config_path)
        self.workspace_config: WorkspaceConfig = deserialize_config(
            workspace_data, WorkspaceConfig
        )

        logger.debug(f"Loading local build config from {self.local_build_config_path}")
        local_build_data = self._load_json_file(self.local_build_config_path)
        self.local_build_config = deserialize_config(local_build_data, LocalBuildConfig)

        logger.debug(f"Loading global build config from {self.global_config_path}")
        global_config_data = self._load_json_file(self.global_config_path)
        self.global_config: GlobalConfig = deserialize_config(
            global_config_data, GlobalConfig
        )

    def _resolve_build_profiles(self) -> Dict[str, BuildProfile]:
        """
        Resolves the active build profiles by loading global definitions and
        overwriting them with local ad-hoc definitions from .puck-build.json.

        """
        logger.debug("Resolving build profiles")

        resolved_profiles: Dict[str, BuildProfile] = {}

        for global_profile in self.global_config.profiles:
            resolved_profiles[global_profile.name] = global_profile
        logger.debug(
            f"Found {len(resolved_profiles)} global profiles: {list(resolved_profiles.keys())}"
        )

        logger.debug("Processing local build profiles")
        for entry in self.local_build_config.profiles:
            if isinstance(entry, str):
                # Reference to a profile by name
                logger.debug(f"Referencing global build profile: {entry}")
                profile_name = entry
                if profile_name not in resolved_profiles:
                    raise ValueError(
                        f"Build profile reference error: Profile '{profile_name}' "
                        f"in '{self.local_build_config_path}' is neither globally defined nor an ad-hoc profile."
                    )
                logger.debug(f"Found referenced global profile: {profile_name}")
            elif isinstance(entry, dict):
                # Local ad-hoc profile (Full definition)
                if "name" not in entry:
                    raise ValueError(
                        f"Ad-hoc profile in '{self.local_build_config_path}' is missing the mandatory 'name' key."
                    )
                logger.debug(f"Found local ad-hoc profile: {entry['name']}")
                ad_hoc_profile = deserialize_config(entry, BuildProfile)

                if ad_hoc_profile.inherits_from:
                    logger.debug(
                        f"Local ad-hoc profile inherits from global profile: {ad_hoc_profile.inherits_from}"
                    )
                    if ad_hoc_profile.inherits_from not in resolved_profiles:
                        raise ValueError(
                            f"Build profile inheritance error: Profile '{ad_hoc_profile.inherits_from}' "
                            f"in '{self.local_build_config_path}' is neither globally defined nor an ad-hoc profile."
                        )
                    ad_hoc_profile = deserialize_config(
                        self._deep_merge(
                            asdict(resolved_profiles[ad_hoc_profile.inherits_from]),
                            entry,
                        ),
                        BuildProfile,
                    )

                if ad_hoc_profile.name in resolved_profiles:
                    if not ad_hoc_profile.is_override:
                        logger.warning(
                            f"Local ad-hoc profile already exists: {entry['name']}"
                        )
                elif ad_hoc_profile.is_override:
                    logger.warning(
                        f"Local ad-hoc profile is marked as override but no profile with the same name already exists: {entry['name']}"
                    )
                resolved_profiles[ad_hoc_profile.name] = ad_hoc_profile
                logger.debug(
                    f"Local ad-hoc profile overwritten/added: {ad_hoc_profile.name}"
                )
            else:
                logger.warning(
                    f"Unknown entry type in active profiles array: {entry}. Entry will be ignored."
                )
        logger.debug(
            f"Resolved {len(resolved_profiles)} build profiles: {list(resolved_profiles.keys())}"
        )
        return resolved_profiles

    def _get_project_path(self, p_def: ProjectDefinition) -> Path:
        """
        Calculates the absolute file system path for a project based on
        its definition (p_def).
        """
        relative_path_part = p_def.path if p_def.path else p_def.name
        project_absolute_path = self.workspace_root / relative_path_part

        return project_absolute_path

    def _create_projects_from_config(self) -> None:
        """
        Creates the runtime Project objects (self.projects) from the raw
        ProjectDefinition models loaded from puck-workspace.json.
        """
        self._projects: Dict[str, Project] = {}

        for p_def in self.workspace_config.projects:
            project = Project(
                name=p_def.name,
                path=self._get_project_path(p_def),
                repository_url=p_def.repository_url,
                depends_on=p_def.depends_on,
                conan_editable=p_def.conan_editable,
            )
            self._projects[project.name] = project
        logger.debug(f"Successfully loaded {len(self._projects)} projects.")

    def _topological_sort(self) -> List[Project]:
        """
        Performs a Depth-First Search (DFS) based topological sort
        to determine the correct build order. Checks for cycles.
        """
        # Graph state to detect cycles and track progress
        visit_state: Dict[str, VisitState] = {
            name: VisitState.UNVISITED for name in self._projects
        }
        sorted_list: List[Project] = []

        def dfs_visit(project_name: str, path: List[str]):
            """Recursive DFS helper function."""

            if visit_state[project_name] == VisitState.VISITING:
                cycle = path + [project_name]
                raise ValueError(
                    f"Cycle detected in project dependencies: {' -> '.join(cycle)}"
                )

            if visit_state[project_name] == VisitState.VISITED:
                return

            visit_state[project_name] = VisitState.VISITING
            current_project = self._projects[project_name]
            path.append(project_name)

            for dep_name in current_project.depends_on:
                if dep_name not in self._projects:
                    raise ValueError(
                        f"Project '{project_name}' depends on unknown workspace project '{dep_name}'."
                    )

                dfs_visit(dep_name, path)

            visit_state[project_name] = VisitState.VISITED
            path.pop()

            sorted_list.append(current_project)

        for project_name in self._projects.keys():
            if visit_state[project_name] == VisitState.UNVISITED:
                dfs_visit(project_name, [])

        return sorted_list

    def _load_json_file(self, file_path: Path) -> Dict[str, Any]:
        """Reads and parses a JSON file; return an empty dict in case of a missing optional file."""
        if not file_path.exists():
            if (
                file_path.name == self.WORKSPACE_CONFIG_FILE_NAME
                or file_path.name == self.LOCAL_BUILD_CONFIG_FILE_NAME
            ):
                raise FileNotFoundError(
                    f"Mandatory configuration file not found: {file_path}"
                )
            return {}

        try:
            with file_path.open("r", encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(
                f"Failed to parse configuration file {file_path.name}: {e}"
            )
        except Exception as e:
            raise IOError(f"Error reading configuration file {file_path.name}: {e}")

    @staticmethod
    def _deep_merge(
        base_dict: Dict[str, Any], overlay_dict: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Recursively merges overlay_dict into base_dict.
        If a key exists in both and the values are dictionaries, they are merged recursively.
        Otherwise, the value from overlay_dict overwrites the value from base_dict.
        """
        merged_dict = base_dict.copy()

        for key, overlay_value in overlay_dict.items():
            base_value = merged_dict.get(key)

            if isinstance(base_value, dict) and isinstance(overlay_value, dict):
                merged_dict[key] = Workspace._deep_merge(base_value, overlay_value)
            else:
                merged_dict[key] = overlay_value

        return merged_dict


def print_projects_in_build_order(workspace: Workspace) -> None:
    for i, project in enumerate(workspace.projects):
        logger.print(
            f"  {i + 1} (Path: {project.absolute_path.relative_to(workspace.workspace_root)})"
        )
