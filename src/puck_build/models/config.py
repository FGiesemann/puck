# puck_build/models/config.py
#
# Puck - Build Manager for Modular C++-Projects
#
# Copyright (c) 2025 Florian Giesemann
# This file is distributed under the terms of the MIT License

"""
Model for different configuration files.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any


@dataclass
class ConanConfig:
    """Models the 'conan' section of a build profile."""

    profile_name: Optional[str] = None
    settings: Optional[Dict[str, Any]] = field(default_factory=dict)


@dataclass
class BuildConfig:
    """Models the 'build' section of a build profile."""

    tool: Optional[str] = None
    config: Optional[str] = None  # CMake Preset Name, Bazel Target, etc.


@dataclass
class BuildProfile:
    """Defines a complete build profile (global or ad-hoc)."""

    name: str
    description: Optional[str] = None
    inherits_from: Optional[str] = None
    is_override: Optional[bool] = False
    conan: ConanConfig = field(default_factory=ConanConfig)
    build: BuildConfig = field(default_factory=BuildConfig)
    build_directory: Optional[str] = None


@dataclass
class GlobalConfig:
    """The global puck configuration file (in user's home directory)."""

    profiles: List[BuildProfile] = field(default_factory=list)


@dataclass
class LocalBuildConfig:
    """The local puck-build.json in a workspace."""

    profiles: List[Dict[str, Any] | str] = field(default_factory=list)
    skip_build: List[str] = field(default_factory=list)


@dataclass
class ProjectDefinition:
    """Defines a single project in the workspace."""

    name: str
    path: str = ""
    repository_url: Optional[str] = None
    depends_on: List[str] = field(default_factory=list)
    conan_editable: Optional[bool] = False


@dataclass
class WorkspaceConfig:
    """Structure of puck-workspace.json."""

    projects: List[ProjectDefinition] = field(default_factory=list)
