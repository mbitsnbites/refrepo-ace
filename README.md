# Refrepo-Ace

This is a tool for maintaining and synchronizing Git reference repositories.

## About reference repos

A reference repository is a local git repository that can be referenced when
you clone remote repositories, like this:

```bash
git clone --reference /path/to/refrepo.git git@server.com:path/to/remote.git
```

When cloning the remote repository, local objects in the reference repository
will be used instead of downloading them from the remote, when possible. This
saves network bandwidth, disk space and time.

## How it works

Refrepo-Ace is split into two parts:

1. `refrepo_ace` - The "master" of the reference repository.
2. `refrepo_git` - A Git wrapper that communicates with `refrepo_ace`.

### The Ace

`refrepo_ace` is a Python script that updates the contents of a reference repo.
It reads a configuration that specifies which remotes to clone, and updates the
reference repo by fetching objects from all the configured remotes.

The idea is that `refrepo_ace` should run periodically (e.g. every five
minutes), but it is up to the user to arrange the details. One possibility is
to run `refrepo_ace` via a Cron job. Another alternative is to run it in a loop
inside a Docker container (see [Dockerfile](Dockerfile) and
[refrepo-updater.sh](refrepo-updater.sh) for an example solution).

### The Git wrapper

The Git wrapper is merely a convenience tool that automatically makes sure that
the reference repository is used when cloning and fetching from remotes, and it
also updates the Refrepo-Ace configuration with new remotes to add to the
reference repository whenever they are encountered (e.g. during a
`git submodule update` command).

Use it by calling the script directly, like this:

```bash
refrepo_git.py clone git@server.com:path/to/remote.git
```

...or create a symbolic link or alias to the script, like this:

```bash
ln -s path/to/refrepo_git.py $HOME/bin/git
git clone git@server.com:path/to/remote.git
```

**Note:** Do not forget to set the necessary environment variables (see below).

## The configuration

Inside the reference repository root folder, there is a configuration folder
(called `conf` by default). To request that a remote shall be added to the
reference repository, add a single file in the `conf` folder with the file
extension `.remote`, and let the contents of the file be the remote URL
(encoded as an UTF-8 string).

For instance:

```bash
echo "git@server.com:path/to/remote.git" > conf/my_important_repo.remote
```

If you use `refrepo_git` to clone your repositories, it will automatically
add new remotes to the configuration directory.

## Environment variables

Both `refrepo_ace` and `refrepo_git` understand the following environment
variables:

| Name | Default | Description |
| --- | --- | --- |
| REFREPO_ACE_ROOT_DIR | - | The root directory of the reference repository and configuration directory (must be specified) |
| REFREPO_ACE_REPO | refrepo.git | The name of the reference repository |
| REFREPO_ACE_CONF_DIR | conf | The name of the configuration directory |
