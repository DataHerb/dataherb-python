import os, sys
import click

import inquirer
from dataherb.parse.model_json import IGNORED_FOLDERS_AND_FILES
from loguru import logger

logger.remove()
logger.add(sys.stderr, level="INFO", enqueue=True)


def describe_file(file):
    """
    describe_file [summary]

    [extended_summary]

    :param file: [description]
    :type file: [type]
    :return: [description]
    :rtype: [type]
    """
    questions = [
        inquirer.Text("name", message=f"How would you like to name the file: {file}?"),
        inquirer.Text("description", message=f"What is {file} about?"),
        inquirer.Text(
            "updated_at",
            message=f"When was {file} last updated? In ISO date format such as 2020-02-17.",
        ),
    ]

    answers = inquirer.prompt(questions)
    meta = {
        "name": answers.get("name"),
        "description": answers.get("description"),
        "updated_at": answers.get("updated_at"),
    }

    return meta


def get_metadata_uri(answers):
    """
    get_metadata_uri reconstructs the datapackage uri from the user's answers.
    """

    if answers.get("source") == "git":
        git_repo_link = answers.get("uri")
        git_repo = "/".join(git_repo_link[:-4].split("/")[-2:])
        metadata_uri = (
            f"https://raw.githubusercontent.com/{git_repo}/main/dataherb.json"
        )
    elif answers.get("source") == "s3":
        s3_uri = answers.get("uri", "")
        if s3_uri.endswith("/"):
            s3_uri = s3_uri[:-1]
        metadata_uri = f"{s3_uri}/dataherb.json"
    else:
        click.echo(f'source type {answers.get("source")} is not supported.')

    return metadata_uri


def describe_dataset():
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


def where_is_dataset(directory):
    """
    where_is_dataset asks the user where the dataset is located.
    """
    try:
        folders = []
        for root, dirs, files in os.walk(directory):
            for d in dirs:
                if d not in IGNORED_FOLDERS_AND_FILES:
                    folders.append(os.path.relpath(os.path.join(root, d), "."))
    except Exception as e:
        logger.error("Can not get a list of folders in current directory.")
        folders = []

    folders = [i for i in folders if not i.startswith(".")]

    if folders:
        questions = [
            inquirer.List(
                "dataset_folder",
                message="Which folder contains the data file?",
                choices=folders,
            )
        ]
    else:
        questions = [
            inquirer.Path(
                "dataset_folder",
                message="Which folder will you place the data files?",
                path_type=inquirer.Path.DIRECTORY,
            )
        ]

    answers = inquirer.prompt(questions)
    dataset_folder = answers.get("dataset_folder")

    return dataset_folder
