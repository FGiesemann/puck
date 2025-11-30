# puck_build/tools/cmake.py
#
# Puck - Build Manager for Modular C++-Projects
#
# Copyright (c) 2025 Florian Giesemann
# This file is distributed under the terms of the MIT License

"""
CMake operations.
"""

import subprocess
from pathlib import Path
from typing import List, Optional


class CMakeToolError(Exception):
    """Custom exception for CMake tool failures."""

    pass


class CMakeTool:
    def build(
        self,
        project_path: Path,
        preset_name: Optional[str],
        build_path: Optional[str],
        build_target: str,
    ) -> None:
        """
        Executes the CMake build command. Selects between Preset-based or Path-based build.
        """
        command: List[str] = ["cmake", "--build"]

        if preset_name:
            command.extend(["--preset", preset_name])
        elif build_path:
            command.append(build_path)
        else:
            raise CMakeToolError(
                "Build configuration failed: Either 'preset_name' or 'build_path' must be provided."
            )

        command.extend(["--target", build_target])

        try:
            subprocess.run(
                command,
                check=True,
                cwd=project_path,
            )
        except subprocess.CalledProcessError as e:
            raise CMakeToolError(
                f"CMake build failed with return code {e.returncode} in directory {project_path}."
            )
        except FileNotFoundError:
            raise CMakeToolError(
                "CMake command not found. Is CMake installed and in PATH?"
            )
