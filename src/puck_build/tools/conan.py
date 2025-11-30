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
from typing import Dict, Any, Optional


class ConanToolError(Exception):
    """Custom exception for Conan tool failures."""

    pass


class ConanTool:
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
            command.append(f"-s {key}={value}")
        if install_folder:
            command.append(f"--output-folder={install_folder}")

        try:
            subprocess.run(
                command,
                check=True,
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
