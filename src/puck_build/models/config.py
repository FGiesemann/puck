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

    profile_name: str
    settings: Dict[str, Any] = field(default_factory=dict)


@dataclass
class BuildConfig:
    """Models the 'build' section of a build profile."""

    tool: str
    config: Optional[str] = None  # CMake Preset Name, Bazel Target, etc.


@dataclass
class BuildProfile:
    """Defines a complete build profile (global or ad-hoc)."""

    name: str
    description: Optional[str] = None
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

    profiles: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class ProjectDefinition:
    """Defines a single project in the workspace."""

    name: str
    path: str = ""
    repository_url: Optional[str] = None
    dependencies: List[str] = field(default_factory=list)


@dataclass
class WorkspaceConfig:
    """Structure of puck-workspace.json."""

    projects: List[ProjectDefinition] = field(default_factory=list)
