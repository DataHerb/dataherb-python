import sys

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

    return metadata_uri


def describe_dataset() -> dict:
    """
    describe_dataset asks the user to specify some basic info about the dataset
    """
    questions = [
        inquirer.List(
            "source",
            message="Where is/will be the dataset synced to?",
            choices=["git", "s3"],
        ),
        inquirer.Text("name", message="How would you like to name the dataset?"),
        inquirer.Text("id", message="Please specify a unique id for the dataset"),
        inquirer.Text(
            "description",
            message="What is the dataset about? This will be the description of the dataset.",
        ),
        inquirer.Text(
            "uri",
            message="What is the dataset's URI? This will be the URI of the dataset.",
        ),
    ]

    answers = inquirer.prompt(questions)

    metadata_uri = get_metadata_uri(answers)

    meta = {
        "source": answers.get("source"),
        "name": answers.get("name", ""),
        "id": answers["id"],
        "description": answers.get("description", ""),
        "uri": answers.get("uri", ""),
        "metadata_uri": metadata_uri,
    }

    return meta
