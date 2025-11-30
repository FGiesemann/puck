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

from puck_build.utils.logger import logger


class CMakeToolError(Exception):
    """Custom exception for CMake tool failures."""

    pass


class CMakeTool:
    def __init__(self, dry_run: bool):
        self._dry_run = dry_run

    def _execute(self, command: List[str], cwd: Path):
        """Internal helper to either execute or log the command."""
        command_str = " ".join(command)

        if self._dry_run:
            logger.print(
                f"[CMAKE] Executing: {command_str} in directory {cwd.as_posix()}"
            )
            return

        logger.debug(f"Executing: {command_str} in directory {cwd.as_posix()}")
        subprocess.run(command, check=True, cwd=cwd)

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
            self._execute(
                command,
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
