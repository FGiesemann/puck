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
from typing import List
from puck_build.utils.logger import logger


class GitToolError(Exception):
    """Custom exception for Git tool failures."""

    pass


class GitTool:
    def __init__(self, dry_run: bool):
        self._dry_run = dry_run

    def _execute(self, command: List[str], cwd: Path):
        """Internal helper to either execute or log the command."""
        command_str = " ".join(command)

        if self._dry_run:
            logger.print(
                f"[GIT] Executing: {command_str} in directory {cwd.as_posix()}"
            )
            return

        logger.debug(f"Executing: {command_str} in directory {cwd.as_posix()}")
        subprocess.run(command, check=True, cwd=cwd)

    def clone_repo(self, url: str, target_dir: Path) -> None:
        """Clones a repository recursively into the target directory."""
        # --recursive is crucial for submodules
        if not self._dry_run:
            target_dir.parent.mkdir(parents=True, exist_ok=True)

        command = ["git", "clone", "--recursive", url, target_dir.as_posix()]
        logger.debug(f"Executing: {' '.join(command)}")

        try:
            self._execute(command, Path("."))
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
            self._execute(fetch_command, cwd=repo_dir)
            self._execute(pull_command, cwd=repo_dir)
            self._execute(submodule_command, cwd=repo_dir)
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
        reset_command = ["git", "reset", "--hard", "@{u}"]
        clean_command = ["git", "clean", "-fdx"]
        submodule_command = ["git", "submodule", "update", "--init", "--recursive"]

        try:
            self._execute(["git", "fetch", "--all"], cwd=repo_dir)
            self._execute(stash_command, cwd=repo_dir)
            self._execute(reset_command, cwd=repo_dir)
            self._execute(clean_command, cwd=repo_dir)
            self._execute(submodule_command, cwd=repo_dir)
        except subprocess.CalledProcessError as e:
            raise GitToolError(
                f"Git clean failed in {repo_dir.name} with return code {e.returncode}."
            )
