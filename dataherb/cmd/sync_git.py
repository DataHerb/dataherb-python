from email.utils import parsedate
import json
import sys
from pathlib import Path

import click
import git
import giturlparse


def is_git_repo(path: Path) -> bool:
    """
    checks if path is a git repo

    :param path: path to check
    """
    try:
        _ = git.Repo(path).git_dir
        return True
    except git.exc.InvalidGitRepositoryError:
        return False


def get_dataherb(source: Path) -> dict:
    """
    get dataherb.json from source

    :param source: local folder
    """

    if not (source / "dataherb.json").exists():
        click.echo(
            f"No dataherb.json found in {source}. Please run `dataherb create` first."
        )
        sys.exit()

    with open(source / "dataherb.json", "r") as f:
        data = json.load(f)

    return data


def upload_dataset_to_git(
    source: Path, target: str, experimental: bool = False
) -> None:
    """
    uploads local folder to remote

    :param source: local folder
    :param target: remote url
    :param experimental: experimental flag
    """

    is_git_initialized = is_git_repo(source)

    if not experimental:
        text = (
            f"git sync is still a WIP.\n"
            f"Please go to {source} and sync your git repository to {target} manually.\n"
        )
        if is_git_initialized:
            text += f"Note: simply add, commit and push."
        else:
            text += f"Note: git init your repo, commit, add remote {target}, and push."
        click.echo(text)
    else:
        if is_git_initialized:
            repo = git.Repo(source)
            repo.index.add(["*"])
            repo.index.commit("created datset: added dataherb.json")

            if len(repo.remotes) == 0:
                origin = repo.create_remote("origin", target)
                assert origin.exists()
                origin.fetch()
                repo.create_head("master", origin.refs.master).set_tracking_branch(
                    origin.refs.master
                ).checkout()
                origin.push()
            else:
                repo.git.push()
        else:
            repo = git.Repo.init(source)
            repo.git.add(["*"])
            repo.index.commit("initial commit")
            origin = repo.create_remote("origin", target)
            assert origin.exists()
            origin.fetch()
            repo.create_head("master", origin.refs.master).set_tracking_branch(
                origin.refs.master
            ).checkout()
            origin.push()


def remote_git_repo(metadata_url: str):
    """
    parse a remote git repo url

    :param metadata_url: remote url to metadata file
    """

    parsed = giturlparse.parse(metadata_url)

    url_host_dispatcher = {"github.com": "https://raw.githubusercontent.com"}

    if parsed.host not in url_host_dispatcher:
        raise ValueError(f"{parsed.host} is not supported.")

    return {
        "metadata_uri": f"{url_host_dispatcher[parsed.host]}{parsed.pathname}",
        "path": parsed.pathname,
        "protocol": parsed.protocol,
        "host": parsed.host,
        "resource": parsed.resource,
        "user": parsed.user,
        "port": parsed.port,
        "name": parsed.name,
        "owner": parsed.owner,
    }
