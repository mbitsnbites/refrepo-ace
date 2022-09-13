#!/usr/bin/env python3
# -*- mode: python; tab-width: 4; indent-tabs-mode: nil; -*-

# -----------------------------------------------------------------------------
# Copyright (c) 2020 Marcus Geelnard
#
# This software is provided 'as-is', without any express or implied warranty.
# In no event will the authors be held liable for any damages arising from the
# use of this software.
#
# Permission is granted to anyone to use this software for any purpose,
# including commercial applications, and to alter it and redistribute it
# freely, subject to the following restrictions:
#
#  1. The origin of this software must not be misrepresented; you must not
#     claim that you wrote the original software. If you use this software in
#     a product, an acknowledgment in the product documentation would be
#     appreciated but is not required.
#
#  2. Altered source versions must be plainly marked as such, and must not be
#     misrepresented as being the original software.
#
#  3. This notice may not be removed or altered from any source distribution.
# -----------------------------------------------------------------------------

import argparse
import logging
import os
from pathlib import Path
import shutil
import subprocess
import sys

_ROOT_DIR_ENV_VAR = "REFREPO_ACE_ROOT_DIR"

_DEFAULT_REPO = "refrepo.git"
_REPO_ENV_VAR = "REFREPO_ACE_REPO"

_DEFAULT_CONF_DIR = "conf"
_CONF_DIR_ENV_VAR = "REFREPO_ACE_CONF_DIR"

_DEFAULT_LOG_LEVEL = "WARNING"
_LOG_LEVEL_ENV_VAR = "REFREPO_ACE_LOG_LEVEL"

LOGGER = logging.getLogger()


def git(args):
    LOGGER.info(f"Invoking: git {' '.join(args)}")
    try:
        subprocess.run(["git"] + args, check=True)
    except Exception as e:
        LOGGER.error(e)
        raise


def git_capture_stdout(args):
    LOGGER.info(f"Invoking (silent): git {' '.join(args)}")
    try:
        return subprocess.run(
            ["git"] + args, stdout=subprocess.PIPE, encoding="utf-8", check=True
        ).stdout
    except Exception as e:
        LOGGER.error(e)
        raise


def init_root(root_dir, repo):
    root_dir.mkdir(parents=True, exist_ok=True)
    repo_path = root_dir / repo
    if repo_path.is_file():
        repo_path.unlink()
    if not repo_path.exists():
        git(["init", "--bare", str(repo_path)])


def get_remotes(root_dir, conf_dir):
    remotes = []
    conf_path = root_dir / conf_dir
    conf_path.mkdir(parents=True, exist_ok=True)
    remote_files = conf_path.glob("*.remote")
    for remote_file in remote_files:
        remote_name = remote_file.stem
        remote_url = remote_file.read_text(encoding="utf-8").strip()
        remotes.append({"name": remote_name, "url": remote_url})

    return remotes


def update(root_dir, repo, conf_dir):
    repo_path = root_dir / repo
    init_root(root_dir, repo)

    # Find existing remotes in the reference repo.
    existing_remotes_set = set(
        git_capture_stdout(["-C", str(repo_path), "remote"]).split()
    )

    # Add new requested remotes.
    requested_remotes = get_remotes(root_dir, conf_dir)
    requested_remotes_set = set()
    for remote in requested_remotes:
        requested_remotes_set.add(remote["name"])
        if remote["name"] not in existing_remotes_set:
            git(
                [
                    "-C",
                    str(repo_path),
                    "remote",
                    "add",
                    remote["name"],
                    remote["url"],
                ]
            )

    # Remove remotes that are no longer requested.
    discardable_remotes = existing_remotes_set - requested_remotes_set
    for remote_name in discardable_remotes:
        print("Removing old remote: " + remote_name)
        git(["-C", str(repo_path), "remote", "remove", remote_name])

    # Fetch remotes.
    git(["-C", str(repo_path), "fetch", "--all"])


def clean_repo(root_dir, repo):
    repo_path = root_dir / repo
    if repo_path.is_dir():
        LOGGER.info(f"Removing {repo_path}")
        shutil.rmtree(repo_path)


def main():
    # Initialize the logger.
    log_level = os.getenv(_LOG_LEVEL_ENV_VAR, default=_DEFAULT_LOG_LEVEL)
    log_format = "[%(filename)s (%(process)d)] %(levelname)s: %(message)s"
    logging.basicConfig(level=getattr(logging, log_level), format=log_format)

    # Get command line arguments.
    parser = argparse.ArgumentParser(description="Manage a reference repo")
    parser.add_argument(
        "--root-dir",
        "-r",
        type=str,
        default="",
        help="root folder for the reference repo and configuration (default: $"
        + _ROOT_DIR_ENV_VAR
        + ")",
    )
    parser.add_argument(
        "--repo",
        type=str,
        default="",
        help="name of the reference repo (default: $"
        + _REPO_ENV_VAR
        + " or "
        + _DEFAULT_REPO
        + ")",
    )
    parser.add_argument(
        "--conf-dir",
        type=str,
        default="",
        help="name of the remotes configuration dir (default: $"
        + _CONF_DIR_ENV_VAR
        + " or "
        + _DEFAULT_CONF_DIR
        + ")",
    )
    parser.add_argument(
        "--clean", action="store_true", help="clean the reference repo (start fresh)"
    )
    args = parser.parse_args()

    # Options can be configured via (in priority order):
    #   - A command line argument
    #   - An environment variable
    #   - A default value
    root_dir = args.root_dir if args.root_dir else os.getenv(_ROOT_DIR_ENV_VAR)
    if not root_dir:
        LOGGER.error(f"Please specify the root directory with ${_ROOT_DIR_ENV_VAR}")
        sys.exit(1)
    root_dir = Path(root_dir)

    repo = Path(
        args.repo if args.repo else os.getenv(_REPO_ENV_VAR, default=_DEFAULT_REPO)
    )

    conf_dir = Path(
        args.conf_dir
        if args.conf_dir
        else os.getenv(_CONF_DIR_ENV_VAR, default=_DEFAULT_CONF_DIR)
    )

    # Optionally clean (remove) the refrence repo before updating.
    if args.clean:
        clean_repo(root_dir=root_dir, repo=repo)

    update(root_dir=root_dir, repo=repo, conf_dir=conf_dir)


if __name__ == "__main__":
    main()
