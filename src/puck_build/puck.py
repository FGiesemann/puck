# puck_build/puck.py
#
# Puck - Build Manager for Modular C++-Projects
#
# Copyright (c) 2025 Florian Giesemann
# This file is distributed under the terms of the MIT License

import argparse
import sys
from pathlib import Path
from puck_build.models.workspace import (
    ExistingPathHandling,
    Workspace,
    WorkspaceNotFoundError,
    InvalidWorkspaceConfigError,
    print_projects_in_build_order,
)
from puck_build.utils.logger import (
    LogLevel,
    logger,
)
from typing import NoReturn


def handle_fatal_error(message: str) -> NoReturn:
    logger.error(f"Critical error: {message}")
    sys.exit(1)


def parse_cli_args() -> argparse.Namespace:
    """
    Parses command-line arguments using argparse to define sub-commands.

    Returns:
        The Namespace object containing all parsed arguments.
    """

    parser = argparse.ArgumentParser(
        description="Puck: A build manager for modular C++-Projects.",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="count",
        default=0,
        help="Increase verbosity level (e.g., -v, -vv, -vvv for debug).",
    )

    subparsers = parser.add_subparsers(
        dest="command",
        required=True,
        help="The primary action to perform (e.g., 'puck build', 'puck setup').",
    )

    subparsers.add_parser(
        "check",
        help="Only performs workspace validation and topological analysis without performing any actions.",
    )

    parser_setup = subparsers.add_parser(
        "setup",
        help="Clones all external repositories and prepares the workspace for initial use.",
    )
    parser_setup.add_argument(
        "--handle-existing",
        type=ExistingPathHandling,
        default=ExistingPathHandling.FAIL,
        choices=list(ExistingPathHandling),
        metavar="{fail,skip,overwrite}",
        help="How to handle existing project directories.",
    ).type = lambda s: ExistingPathHandling[s.upper()]

    parser_build = subparsers.add_parser(
        "build",
        help="Builds the entire workspace in the topologically sorted order.",
    )
    parser_build.add_argument(
        "--projects",
        "-p",
        nargs="+",
        help="List of specific project names to build (e.g., 'Util Core'). If omitted, all projects are built.",
    )
    parser_build.add_argument(
        "--profiles",
        nargs="+",
        default=None,
        help="List of Conan profiles to use for building (e.g., 'gcc_release clang_debug'). If omitted, all profiles are built.",
    )

    return parser.parse_args()


def main():
    args = parse_cli_args()
    if args.verbose >= 3:
        logger.min_level = LogLevel.DEBUG
    elif args.verbose == 2:
        logger.min_level = LogLevel.VERBOSE
    elif args.verbose == 1:
        logger.min_level = LogLevel.INFO
    else:
        logger.min_level = LogLevel.WARNING

    start_dir: Path = Path.cwd()

    # handle "create" command that doesn't use a pre-defined workspace here

    try:
        workspace = Workspace(start_dir=start_dir)

        logger.info("Workspace configuration found and understood:")
        logger.info(f"`- Workspace root: {workspace.workspace_root}")

        if args.command == "check":
            logger.debug("command check")
            logger.print("Workspace validated. Projects in build order:")
            print_projects_in_build_order(workspace)
        elif args.command == "setup":
            logger.debug("command setup")
            workspace.setup_workspace(args.handle_existing)
            logger.debug("command build")
        elif args.command == "build":
            # TODO: Build all or selected projects
            pass
    except WorkspaceNotFoundError as e:
        handle_fatal_error(f"Workspace configuration could not be found: {e}")
    except (InvalidWorkspaceConfigError, ValueError, IOError) as e:
        handle_fatal_error(f"Invalid workspace configuration: {e}")
    except Exception as e:
        handle_fatal_error(f"Unexpected error: {e}")


if __name__ == "__main__":
    main()
