import os

import inquirer
from dataherb.parse.model import IGNORED_FOLDERS_AND_FILES, STATUS_CODE, MetaData
from loguru import logger


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


def describe_dataset():
    """
    describe_dataset asks the user to specify some basic info about the dataset
    """
    questions = [
        inquirer.Text("name", message="How would you like to name the dataset?"),
        inquirer.Text(
            "description",
            message="What is the dataset about? This will be the description of the dataset.",
        ),
    ]

    answers = inquirer.prompt(questions)
    meta = {
        "name": answers.get("name", ""),
        "description": answers.get("description", ""),
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