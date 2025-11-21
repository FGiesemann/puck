from pathlib import Path
import subprocess
from typing import List
import json
from puck_build.utils.logger import logger


class CMakeToolError(RuntimeError):
    """Custom exception raised for failed CMake operations."""

    pass


class CMakeTool:
    def __init__(self):
        """Initialize the CMake tool."""
        pass

    def get_available_presets(self, project_path: Path) -> List[str]:
        """
        Lists the names of all available configure presets for the project by
        calling 'cmake --list-presets'.


        Args:
            project_path: Path to the project folder.

        Returns:
            List of configure presets.

        Raises:
            CMakeToolError: If CMake could not be called.
        """
        logger.debug(f"Checking CMake presets in: {project_path}")

        command: List[str] = [
            "cmake",
            "--list-presets",
            "--json",
        ]

        try:
            result = subprocess.run(
                command,
                check=True,
                capture_output=True,
                text=True,
                cwd=project_path,
            )
            data = json.loads(result.stdout)
            configure_presets = data.get("configurePresets", [])
            return [p["name"] for p in configure_presets]

        except subprocess.CalledProcessError as e:
            raise CMakeToolError(
                f"CMake list presets failed in '{project_path.name}'. "
                f"Stderr: {e.stderr.strip()}"
            )
        except FileNotFoundError:
            raise CMakeToolError(
                "CMake executable not found. Please ensure CMake is installed and available in your PATH."
            )
        except json.JSONDecodeError:
            raise CMakeToolError(
                "Failed to decode JSON output from 'cmake --list-presets'."
            )
        except KeyError:
            raise CMakeToolError(
                "JSON output from 'cmake --list-presets' missing expected 'configurePresets' key."
            )

    def build(self, project_path: Path, preset_name: str, build_target: str) -> None:
        """
        Build a project with CMake.

        Args:
            project_path: Path to the project folder.
            preset_name: Name of the configure or build preset.
            build_target: The build target (e.g., 'all', 'install', ...).

        Raises:
            CMakeToolError: In case of errors during the build process.
        """
        logger.print(
            f"  CMAKE: Starting build for project '{project_path.name}' using preset '{preset_name}' (Target: {build_target})."
        )

        command = [
            "cmake",
            "--build",
            "--preset",
            preset_name,
            "--target",
            build_target,
        ]

        try:
            logger.debug(
                f"Running CMake command: {' '.join(command)} in {project_path}"
            )
            subprocess.run(
                command,
                check=True,
                cwd=project_path,
            )

        except subprocess.CalledProcessError as e:
            raise CMakeToolError(
                f"CMake build failed for preset '{preset_name}' and target '{build_target}' in '{project_path.name}'. "
                f"Return code: {e.returncode}"
            )
        except FileNotFoundError:
            raise CMakeToolError(
                "CMake executable not found. Please ensure CMake is installed and available in your PATH."
            )
