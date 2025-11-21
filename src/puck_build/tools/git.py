from pathlib import Path
import subprocess
from typing import List


class GitToolError(RuntimeError):
    """Custom exception raised for failed Git operations."""

    pass


class GitTool:
    def __init__(self, cwd: Path):
        """Initializes the Git tool, setting the working directory."""
        self.cwd = cwd

    def clone(self, url: str, target_dir: Path, recursive: bool = False) -> None:
        """
        Clones a repository into a target directory.

        Args:
            url: The repository URL.
            target_dir: The path where the repository should be cloned (must be a full Path).
            recursive: If True, clones submodules recursively.

        Raises:
            GitToolError: If the git command fails or git executable is not found.
        """
        command: List[str] = [
            "git",
            "clone",
            "--quiet",
            url,
            str(target_dir),
        ]

        if recursive:
            command.insert(2, "--recursive")

        try:
            subprocess.run(
                command, check=True, capture_output=True, text=True, cwd=self.cwd
            )

        except subprocess.CalledProcessError as e:
            raise GitToolError(
                f"Git clone failed for URL '{url}'. Stderr: {e.stderr.strip()}"
            )
        except FileNotFoundError:
            raise GitToolError(
                "Git executable not found. Please ensure Git is installed and available in your PATH."
            )

    def update_submodules(self, directory: Path) -> None:
        """
        Updates submodules in an existing repository directory.
        """
        command = ["git", "submodule", "update", "--init", "--recursive", "--remote"]
        try:
            subprocess.run(
                command, check=True, capture_output=True, text=True, cwd=directory
            )
        except subprocess.CalledProcessError as e:
            raise GitToolError(
                f"Git submodule update failed in directory '{directory}'. "
                f"Stderr: {e.stderr.strip()}"
            )
