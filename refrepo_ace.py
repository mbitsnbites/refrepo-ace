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


def init_root(root_dir, repo):
    root_dir.mkdir(parents=True, exist_ok=True)
    repo_path = root_dir / repo
    if repo_path.is_file():
        repo_path.unlink()
    if not repo_path.exists():
        subprocess.run(["git", "init", "--bare", str(repo_path)], check=True)


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
        subprocess.run(
            ["git", "-C", str(repo_path), "remote"],
            stdout=subprocess.PIPE,
            encoding="utf-8",
            check=True,
        ).stdout.split()
    )

    # Add new requested remotes.
    requested_remotes = get_remotes(root_dir, conf_dir)
    requested_remotes_set = set()
    for remote in requested_remotes:
        requested_remotes_set.add(remote["name"])
        if remote["name"] not in existing_remotes_set:
            subprocess.run(
                [
                    "git",
                    "-C",
                    str(repo_path),
                    "remote",
                    "add",
                    remote["name"],
                    remote["url"],
                ],
                check=True,
            )

    # Remove remotes that are no longer requested.
    discardable_remotes = existing_remotes_set - requested_remotes_set
    for remote_name in discardable_remotes:
        print("Removing old remote: " + remote_name)
        subprocess.run(
            ["git", "-C", str(repo_path), "remote", "remove", remote_name], check=True
        )

    # Fetch remotes.
    subprocess.run(["git", "-C", str(repo_path), "fetch", "--all"], check=True)


def clean_repo(root_dir, repo):
    repo_path = root_dir / repo
    if repo_path.is_dir():
        shutil.rmtree(repo_path)


def main():
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
        print("Error: Please specify the root directory")
        sys.exit(1)
    root_dir = Path(root_dir)

    repo = args.repo if args.repo else os.getenv(_REPO_ENV_VAR)
    if not repo:
        repo = _DEFAULT_REPO
    repo = Path(repo)

    conf_dir = args.conf_dir if args.conf_dir else os.getenv(_CONF_DIR_ENV_VAR)
    if not conf_dir:
        conf_dir = _DEFAULT_CONF_DIR
    conf_dir = Path(conf_dir)

    # Optionally clean (remove) the refrence repo before updating.
    if args.clean:
        clean_repo(root_dir=root_dir, repo=repo)

    update(root_dir=root_dir, repo=repo, conf_dir=conf_dir)


if __name__ == "__main__":
    main()
