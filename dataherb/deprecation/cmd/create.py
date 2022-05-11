import os, sys
import inquirer
from dataherb.parse.utils import IGNORED_FOLDERS_AND_FILES
from loguru import logger

logger.remove()
logger.add(sys.stderr, level="INFO", enqueue=True)


def describe_file(file: str):
    """
    [Deprecated]

    describe_file asks the user to specify some basic info about the file

    :param file: file to describe
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


def where_is_dataset(directory):
    """
    where_is_dataset asks the user where the dataset is located.

    :param directory: directory to search in
    """
    try:
        folders = []
        for root, dirs, _ in os.walk(directory):
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
