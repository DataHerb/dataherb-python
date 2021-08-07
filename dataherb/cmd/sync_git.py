import sys
import json
import click
import git
from pathlib import Path


def is_git_repo(path):
    try:
        _ = git.Repo(path).git_dir
        return True
    except git.exc.InvalidGitRepositoryError:
        return False


def get_dataherb(source):

    if not (Path(source) / "dataherb.json").exists():
        click.echo(
            f"No dataherb.json found in {source}. Please run `dataherb create` first."
        )
        sys.exit()

    with open(Path(source) / "dataherb.json", "r") as f:
        data = json.load(f)

    return data


def upload_dataset_to_git(source, target, experimental=False):
    """uploads local folder to remote"""

    is_git_initialized = is_git_repo(source)

    if not experimental:
        text = (
            f"git sync is still a WIP.\n"
            f"Please go to {source} and sync your git repository to {target} manually.\n"
        )
        if is_git_initialized:
            text += (
                f"Note: simply add, commit and push."
            )
        else:
            text += (
                f"Note: git init your repo, commit, add remote {target}, and push."
            )
        click.echo(text)
    else:
        if is_git_initialized:
            repo = git.Repo(source)
            repo.index.add(["*"])
            repo.index.commit("created datset: added dataherb.json")

            if len(repo.remotes) == 0:
                origin = repo.create_remote('origin', target)
                assert origin.exists()
                origin.fetch()
                repo.create_head('master', origin.refs.master).set_tracking_branch(origin.refs.master).checkout()
                origin.push()
            else:
                repo.git.push()
        else:
            repo = git.Repo.init(source)
            repo.git.add(["*"])
            repo.index.commit("initial commit")
            origin = repo.create_remote('origin', target)
            assert origin.exists()
            origin.fetch()
            repo.create_head('master', origin.refs.master).set_tracking_branch(origin.refs.master).checkout()
            origin.push()

