import sys
from typing import Optional

import click
import inquirer
from loguru import logger

logger.remove()
logger.add(sys.stderr, level="INFO", enqueue=True)


def get_metadata_uri(answers: dict, branch: str = "main") -> str:
    """
    get_metadata_uri reconstructs the datapackage uri from the user's answers.

    :param answers: answers from inquirer prompt
    """

    if answers.get("source") == "git":
        git_repo_link = answers.get("uri", "")
        git_repo = "/".join(git_repo_link[:-4].split("/")[-2:])
        metadata_uri = (
            f"https://raw.githubusercontent.com/{git_repo}/{branch}/dataherb.json"
        )
    elif answers.get("source") == "s3":
        s3_uri = answers.get("uri", "")
        if s3_uri.endswith("/"):
            s3_uri = s3_uri[:-1]
        metadata_uri = f"{s3_uri}/dataherb.json"
    else:
        click.echo(f'source type {answers.get("source")} is not supported.')
        metadata_uri = ""

    return metadata_uri


def describe_dataset(defaults: Optional[dict] = None) -> dict:
    """
    describe_dataset asks the user to describe the dataset.

    :param defaults: inferred metadata used as default answers
    """
    d = defaults or {}
    owner: dict = d["owner"] if isinstance(d.get("owner"), dict) else {}
    questions = [
        inquirer.List(
            "source",
            message="Where is/will be the dataset synced to?",
            choices=["git", "s3", "http", "local"],
        ),
        inquirer.Text(
            "name",
            message="How would you like to name the dataset?",
            default=d.get("name", ""),
        ),
        inquirer.Text(
            "id",
            message="Please specify a unique id for the dataset",
            default=d.get("id", ""),
        ),
        inquirer.Text(
            "description",
            message="What is the dataset about? This will be the description of the dataset.",
        ),
        inquirer.Text(
            "uri",
            message="What is the dataset's URI (git repo URL, s3://bucket/prefix/, https://...)?",
        ),
        inquirer.Text(
            "owner_team", message="Which team owns it?", default=owner.get("team", "")
        ),
        inquirer.Text(
            "owner_email", message="Contact email?", default=owner.get("email", "")
        ),
        inquirer.Text("tags", message="Tags, comma separated"),
        inquirer.Text("license", message="License or usage terms"),
        inquirer.List(
            "update_frequency",
            message="How often is it updated?",
            choices=[
                "static",
                "hourly",
                "daily",
                "weekly",
                "monthly",
                "yearly",
                "irregular",
            ],
        ),
        inquirer.Text(
            "status_job",
            message="Id of the job that refreshes it (for status monitoring; leave blank if none)",
        ),
    ]

    answers = inquirer.prompt(questions) or {}

    meta = {
        "source": answers.get("source"),
        "name": answers.get("name", ""),
        "id": answers.get("id") or d.get("id"),
        "description": answers.get("description", ""),
        "uri": answers.get("uri", ""),
        "owner": {
            "team": answers.get("owner_team", ""),
            "email": answers.get("owner_email", ""),
        },
        "tags": [t.strip() for t in answers.get("tags", "").split(",") if t.strip()],
        "license": answers.get("license", ""),
        "update_frequency": answers.get("update_frequency", ""),
        "status_job": answers.get("status_job", ""),
    }
    if answers.get("source") in ("git", "s3") and answers.get("uri"):
        meta["metadata_uri"] = get_metadata_uri(answers)

    return meta
