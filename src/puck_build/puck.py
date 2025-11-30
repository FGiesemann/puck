# puck_build/puck.py
#
# Puck - Build Manager for Modular C++-Projects
#
# Copyright (c) 2025 Florian Giesemann
# This file is distributed under the terms of the MIT License

import argparse
import sys
from pathlib import Path
from puck_build.models.workspace import Workspace
from puck_build.utils.logger import Logger, calculate_log_level


def main():
    parser = argparse.ArgumentParser(
        description="puck: A clean and modern build orchestration tool for C++ projects.",
        formatter_class=argparse.RawTextHelpFormatter,
    )

    parser.add_argument(
        "-v",
        "--verbose",
        action="count",
        default=0,
        help="Increase logging verbosity (e.g., -v for INFO, -vv for VERBOSE, -vvv for DEBUG).",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    setup_parser = subparsers.add_parser(
        "setup", help="Clones or updates all sub-projects."
    )
    setup_parser.add_argument(
        "--clean",
        action="store_true",
        help="Aggressively reset and clean the repositories, discarding local changes.",
    )
    setup_parser.set_defaults(func=lambda args, ws: ws.setup_projects(clean=args.clean))

    install_parser = subparsers.add_parser(
        "install",
        help="Installs dependencies for ALL available profiles defined in .puck-build.json.",
    )

    def execute_install(args, ws):
        profile_names = list(ws.resolved_profiles.keys())
        if not profile_names:
            logger.warning(
                "No build profiles are defined in the configuration. Nothing to install."
            )
            return
        logger.info(
            f"Installing dependencies for ALL available profiles: {', '.join(profile_names)}"
        )
        ws.install_projects(profile_names=profile_names)

    install_parser.set_defaults(func=execute_install)

    build_parser = subparsers.add_parser(
        "build", help="Builds projects using CMake and specified build profiles."
    )
    build_parser.add_argument(
        "profiles",
        nargs="*",
        help="List of build profiles to use. If none are specified, ALL available profiles are built.",
    )
    build_parser.add_argument(
        "--target",
        default="all",
        help="Specific CMake target to build (default: 'all').",
    )

    def execute_build(args, ws):
        if not args.profiles:
            profile_names = list(ws.resolved_profiles.keys())
            if not profile_names:
                logger.warning(
                    "No build profiles are defined in the configuration. Nothing to build."
                )
                return
            logger.info(f"Building ALL available profiles: {', '.join(profile_names)}")
        else:
            profile_names = args.profiles
            for p in profile_names:
                if p not in ws.resolved_profiles:
                    logger.error(
                        f"Error: Unknown profile '{p}'. Available profiles: {list(ws.resolved_profiles.keys())}"
                    )
                    sys.exit(1)
        ws.build_projects(profile_names=profile_names, target=args.target)

    build_parser.set_defaults(func=execute_build)

    args = parser.parse_args()

    calculated_log_level = calculate_log_level(args.verbose)
    global logger
    logger = Logger(calculated_log_level)

    try:
        workspace = Workspace(start_dir=Path.cwd())
    except Exception as e:
        logger.error(f"Failed to initialize workspace: {e}")
        sys.exit(1)

    args.func(args, workspace)


if __name__ == "__main__":
    main()
