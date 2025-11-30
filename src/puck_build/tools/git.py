# puck_build/tools/git.py
#
# Puck - Build Manager for Modular C++-Projects
#
# Copyright (c) 2025 Florian Giesemann
# This file is distributed under the terms of the MIT License

"""
Git operations.
"""

import subprocess
from pathlib import Path
from puck_build.utils.logger import logger


class GitToolError(Exception):
    """Custom exception for Git tool failures."""

    pass


class GitTool:
    def clone_repo(self, url: str, target_dir: Path) -> None:
        """Clones a repository recursively into the target directory."""
        # --recursive is crucial for submodules
        command = ["git", "clone", "--recursive", url, target_dir.as_posix()]
        logger.debug(f"Executing: {' '.join(command)}")

        try:
            subprocess.run(command, check=True)
        except subprocess.CalledProcessError as e:
            raise GitToolError(
                f"Git clone failed with return code {e.returncode} for {url}."
            )
        except FileNotFoundError:
            raise GitToolError("Git command not found. Is Git installed and in PATH?")

    def update_repo(self, repo_dir: Path) -> None:
        """Updates an existing repository, fetching and updating submodules recursively."""

        fetch_command = ["git", "fetch", "--all"]
        pull_command = ["git", "pull"]
        submodule_command = ["git", "submodule", "update", "--init", "--recursive"]

        try:
            subprocess.run(fetch_command, check=True, cwd=repo_dir)
            subprocess.run(pull_command, check=True, cwd=repo_dir)
            subprocess.run(submodule_command, check=True, cwd=repo_dir)

        except subprocess.CalledProcessError as e:
            raise GitToolError(
                f"Git update failed in {repo_dir.name} with return code {e.returncode}."
            )

    def clean_repo(self, repo_dir: Path) -> None:
        """
        Aggressively cleans the repository: discards local changes,
        removes untracked files, and resets to the latest remote state.
        """
        logger.info(f"  Cleaning repository: {repo_dir.name}")

        stash_command = ["git", "stash", "push", "-u", "-m", "puck-cleanup-stash"]
        reset_command = ["git", "reset", "--hard", "@{{u}}"]
        clean_command = ["git", "clean", "-fdx"]
        submodule_command = ["git", "submodule", "update", "--init", "--recursive"]

        try:
            subprocess.run(["git", "fetch", "--all"], check=True, cwd=repo_dir)
            subprocess.run(stash_command, check=False, cwd=repo_dir)
            subprocess.run(reset_command, check=True, cwd=repo_dir)
            subprocess.run(clean_command, check=True, cwd=repo_dir)
            subprocess.run(submodule_command, check=True, cwd=repo_dir)

            logger.debug(f"  Successfully cleaned and reset {repo_dir.name}.")

        except subprocess.CalledProcessError as e:
            raise GitToolError(
                f"Git clean failed in {repo_dir.name} with return code {e.returncode}."
            )
