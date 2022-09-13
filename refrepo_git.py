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

import hashlib
import logging
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile

_ROOT_DIR_ENV_VAR = "REFREPO_ACE_ROOT_DIR"

_DEFAULT_REPO = "refrepo.git"
_REPO_ENV_VAR = "REFREPO_ACE_REPO"

_DEFAULT_CONF_DIR = "conf"
_CONF_DIR_ENV_VAR = "REFREPO_ACE_CONF_DIR"

_TRUTHY_VALUES = ("1", "on", "t", "true", "y", "yes")
_DROP_CREDENTIALS_ENV_VAR = "REFREPO_ACE_DROP_CREDENTIALS"

_DEFAULT_LOG_LEVEL = "WARNING"
_LOG_LEVEL_ENV_VAR = "REFREPO_ACE_LOG_LEVEL"

LOGGER = logging.getLogger()


def find_git_exe():
    # Get the search path.
    search_path = os.getenv("PATH", default=os.defpath)

    # Iterate over the search path until we find the true git executable.
    this_script_path = Path(os.path.realpath(__file__))
    search_path = search_path.split(os.pathsep)
    for p in search_path:
        git_path = shutil.which("git", path=p)
        try:
            if git_path and not this_script_path.samefile(os.path.realpath(git_path)):
                return git_path
        except OSError:
            continue

    # If we get this far, we could not find a proper git executable.
    print("refrepo_git: No found git - please install!")
    sys.exit(1)


def wrap_git(args):
    completed = subprocess.run([find_git_exe()] + args)
    if completed.returncode != 0:
        sys.exit(completed.returncode)


def wrap_git_and_exit(args):
    wrap_git(args)
    sys.exit(0)


def get_clone_target_path(args):
    # Drop options to the clone command.
    while args:
        if args[0][0] != "-":
            break
        elif args[0] == "--":
            args = args[1:]
            break
        elif args[0] in [
            "-o",
            "--origin",
            "-b",
            "--branch",
            "-u",
            "--upload-pack",
            "-c",
            "--config",
            "--reference",
            "--reference-if-able",
            "--separate-git-dir",
            "--depth",
            "-j",
            "--jobs",
        ]:
            args = args[2:]
        else:
            args = args[1:]

    # The second parameter, if present, is <directory>.
    if len(args) >= 2:
        return args[1]

    # The first parameter is <repository>, from which we derive the
    # directory name.
    if len(args) >= 1:
        url = args[0]
        idx = url.rfind("/")
        if idx >= 0:
            dir_name = url[(idx + 1) :]
            if dir_name[-4:] == ".git":
                dir_name = dir_name[:-4]
            if len(dir_name) > 0:
                return dir_name

    # If we could not determine the target clone directory, bail...
    raise Exception("Clone target directory could not be determined")


def get_client_repo_root():
    # Special case: When running "git clone ..." we're usually not standing in
    # the Git folder.
    if len(sys.argv) >= 2 and sys.argv[1] == "clone":
        return get_clone_target_path(sys.argv[2:])

    # Check if the user has specified a Git workign folder with -C.
    for k in range(1, len(sys.argv) - 1):
        arg = sys.argv[k]
        if arg == "-C":
            return sys.argv[k + 1]

    # By default: Assume that Git is operating in the CWD.
    return os.getcwd()


def make_remote_name(url):
    # Scheme + domain regex
    # See: https://github.com/git/git/blob/77bd3ea9f54f1584147b594abc04c26ca516d987/url.c#L7-L11
    human_name = re.search(
        # Proper URL (scheme://[user[:password]@]domain.tld/)
        r"(^[A-Za-z][A-Za-z0-9+.-]*://.+?/|"
        # SCP style ([user@]domain.tld:)
        + r"^[^/]+?:|"
        # local file
        + r"^)"
        # Path to repository (/path/to/repo.git)
        + r"(.+?)(\.git)?/?$",
        url,
    ).group(2)
    human_name = human_name.lower().replace("/", "_")
    short_hash = hashlib.md5(url.encode("utf-8")).hexdigest()[:8]
    return human_name + "-" + short_hash


def extract_remote_conf(remotes):
    result = []
    for remote in remotes:
        # We use the fetch URL (and ignore the push URL).
        parts = remote.split()
        if parts[2] == "(fetch)":
            url = parts[1]
            if (
                os.getenv(_DROP_CREDENTIALS_ENV_VAR, default="False").lower()
                in _TRUTHY_VALUES
            ):
                url = re.sub(r"[\w-]*:[\w-]*@", "", url)
            name = make_remote_name(url)
            result.append({"name": name, "url": url})

    return result


def atomic_write(path, data):
    if not path.is_file():
        tmp_file = tempfile.NamedTemporaryFile(
            dir=str(path.parent), mode="w", encoding="utf-8", delete=False
        )
        tmp_file.write(data)
        tmp_path = Path(tmp_file.name)
        try:
            tmp_path.rename(path)
            return True
        except OSError:
            tmp_path.unlink()
            return False


def write_remote_confs(remotes, root_dir, conf_dir):
    target_dir = root_dir / conf_dir
    if not target_dir.is_dir():
        return

    for remote in remotes:
        target_file = (target_dir / remote["name"]).with_suffix(".remote")
        if atomic_write(target_file, remote["url"]):
            LOGGER.info(f"Registered new remote: {target_file}")


def update_required_remotes(root_dir, conf_dir):
    # Find existing remotes in the reference repo.
    repo_root = get_client_repo_root()

    remotes = extract_remote_conf(
        subprocess.run(
            [find_git_exe(), "remote", "-v"],
            stdout=subprocess.PIPE,
            encoding="utf-8",
            check=True,
            cwd=repo_root,
        ).stdout.splitlines()
    )

    remotes += extract_remote_conf(
        subprocess.run(
            [
                find_git_exe(),
                "submodule",
                "--quiet",
                "foreach",
                "--recursive",
                "git remote -v",
            ],
            stdout=subprocess.PIPE,
            encoding="utf-8",
            check=True,
            cwd=repo_root,
        ).stdout.splitlines()
    )

    # Add the required remotes to the refrepo configuration.
    write_remote_confs(remotes, root_dir, conf_dir)


def drop_pre_command_git_args(args):
    while args:
        if args[0][0] != "-":
            break
        if args[0] == "-C" or args[0] == "-c":
            args = args[2:]
        else:
            args = args[1:]

    return args


def inject_reference_repo_arg(args, root_dir, repo):
    repo_path = root_dir / repo
    if not repo_path.is_dir():
        return args

    original_args = args
    args = drop_pre_command_git_args(args)
    dropped_args = len(original_args) - len(args)

    insert_pos = -1
    if len(args) >= 1 and args[0] == "clone":
        insert_pos = 1
    elif len(args) >= 2 and args[0] == "submodule" and args[1] == "add":
        insert_pos = 2
    elif len(args) >= 2 and args[0] == "submodule" and args[1] == "update":
        insert_pos = 2

    args = original_args
    if insert_pos > 0:
        insert_pos += dropped_args
        args.insert(insert_pos, "--reference")
        args.insert(insert_pos + 1, str(repo_path))

    return args


def add_alternates(args, root_dir, repo):
    objects_path = root_dir / repo / "objects"
    if not objects_path.is_dir():
        return

    info_path = Path(get_client_repo_root()) / ".git" / "objects" / "info"
    if not info_path.is_dir():
        return

    alternates_path = info_path / "alternates"
    if not alternates_path.exists():
        alternates_path.touch()

    args = drop_pre_command_git_args(args)

    if len(args) >= 1 and args[0] == "fetch":
        with open(alternates_path, "r+", encoding="utf-8") as f:
            for line in f:
                if Path(line.strip()) == objects_path:
                    break
            else:
                f.write(str(objects_path))
                f.write("\n")


def should_update_remotes(args):
    args = drop_pre_command_git_args(args)

    # Some standard commands that may provide us with new remotes.
    if len(args) >= 1 and args[0] in ["clone", "fetch", "pull", "checkout"]:
        return True

    # "submodule update" may get more remotes (i.e. recursive).
    if len(args) >= 2 and args[0] == "submodule" and args[1] == "update":
        return True

    return False


def main():
    # Initialize the logger.
    log_level = os.getenv(_LOG_LEVEL_ENV_VAR, default=_DEFAULT_LOG_LEVEL)
    log_format = "[%(filename)s (%(process)d)] %(levelname)s: %(message)s"
    logging.basicConfig(level=getattr(logging, log_level), format=log_format)

    # Options can be configured via (in priority order):
    #   - An environment variable
    #   - A default value
    root_dir = os.getenv(_ROOT_DIR_ENV_VAR)
    if not root_dir:
        LOGGER.error(f"Please specify the root directory with ${_ROOT_DIR_ENV_VAR}")
        wrap_git_and_exit(sys.argv[1:])
    root_dir = Path(root_dir)

    repo = Path(os.getenv(_REPO_ENV_VAR, default=_DEFAULT_REPO))
    conf_dir = Path(os.getenv(_CONF_DIR_ENV_VAR, default=_DEFAULT_CONF_DIR))

    args = inject_reference_repo_arg(sys.argv[1:], root_dir, repo)
    add_alternates(sys.argv[1:], root_dir, repo)
    LOGGER.info(f"Wrapping: git {' '.join(args)}")
    wrap_git(args)

    try:
        if should_update_remotes(args):
            update_required_remotes(root_dir, conf_dir)
    except Exception as e:
        LOGGER.error(e)
        pass


if __name__ == "__main__":
    main()
