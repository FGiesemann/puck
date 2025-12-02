# puck_build/tools/conan.py
#
# Puck - Build Manager for Modular C++-Projects
#
# Copyright (c) 2025 Florian Giesemann
# This file is distributed under the terms of the MIT License

"""
Conan operations.
"""

import subprocess
from pathlib import Path
from typing import Dict, Any, List, Optional

from puck_build.utils.logger import logger


class ConanToolError(Exception):
    """Custom exception for Conan tool failures."""

    pass


class ConanTool:
    def __init__(self, dry_run: bool):
        self._dry_run = dry_run

    def _execute(self, command: List[str], cwd: Path):
        """Internal helper to either execute or log the command."""
        command_str = " ".join(command)

        if self._dry_run:
            logger.print(
                f"[CONAN] Executing: {command_str} in directory {cwd.as_posix()}"
            )
            return

        logger.debug(f"Executing: {command_str} in directory {cwd.as_posix()}")
        subprocess.run(command, check=True, cwd=cwd)

    def install(
        self,
        project_path: Path,
        conan_profile_name: str,
        settings: Dict[str, Any],
        install_folder: Optional[str],
    ) -> None:
        """
        Executes the 'conan install' command.
        """
        command = [
            "conan",
            "install",
            project_path.as_posix(),
            f"--profile:host={conan_profile_name}",
        ]

        for key, value in settings.items():
            command.append(f"-s{key}={value}")
        if install_folder:
            command.append(f"--output-folder={install_folder}")

        try:
            self._execute(
                command,
                cwd=project_path,
            )
        except subprocess.CalledProcessError as e:
            raise ConanToolError(
                f"Conan install failed with return code {e.returncode}."
            )
        except FileNotFoundError:
            raise ConanToolError(
                "Conan command not found. Is Conan installed and in PATH?"
            )

    def add_editable(self, project_path: Path) -> None:
        """
        Adds a local project as an editable package to the Conan cache.
        """
        command = ["conan", "editable", "add", "."]

        try:
            self._execute(command, cwd=project_path)
        except subprocess.CalledProcessError as e:
            raise ConanToolError(
                f"Conan editable add failed for  project at {project_path.name} with return code {e.returncode}."
            )
        except FileNotFoundError:
            raise ConanToolError(
                "Conan command not found. Is Conan installed and in PATH?"
            )
