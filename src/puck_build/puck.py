# puck_build/puck.py
#
# Puck - Build Manager for Modular C++-Projects
#
# Copyright (c) 2025 Florian Giesemann
# This file is distributed under the terms of the MIT License

import sys
from pathlib import Path
from puck_build.models.workspace import (
    Workspace,
    WorkspaceNotFoundError,
    InvalidWorkspaceConfigError,
)
from typing import NoReturn


def handle_fatal_error(message: str) -> NoReturn:
    print(f"Critical error: {message}")
    sys.exit(1)


def main():
    try:
        start_dir: Path = Path.cwd()
        workspace = Workspace(start_dir=start_dir)

        print("Workspace configuration found and understood:")
        print(f"  Workspace root: {workspace.workspace_root}")
        print("  Projects in build order:")

        for i, project in enumerate(workspace.projects):
            print(
                f"    {i + 1}. {project.name} (Path: {project.absolute_path.relative_to(workspace.workspace_root)})"
            )
    except WorkspaceNotFoundError as e:
        handle_fatal_error(f"Workspace configuration could not be found: {e}")
    except (InvalidWorkspaceConfigError, ValueError, IOError) as e:
        handle_fatal_error(f"Invalid workspace configuration: {e}")
    except Exception as e:
        handle_fatal_error(f"Unexpected error: {e}")


if __name__ == "__main__":
    main()
