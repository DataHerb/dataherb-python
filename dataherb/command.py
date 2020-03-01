import logging
import os

import click
import inquirer

from dataherb.flora import Flora
from dataherb.parse.model import MetaData, IGNORED_FOLDERS_AND_FILES

__CWD__ = os.getcwd()

logging.basicConfig()
logger = logging.getLogger("dataherb.command")

def describe_file(file):
    questions = [
            inquirer.Text(
                'name',
                message=f"How would you like to name the file: {file}?"
            ),
            inquirer.Text(
                'description',
                message=f"What is {file} about?"
            ),
            inquirer.Text(
                'updated_at',
                message=f"When was {file} last updated? In ISO date format such as 2020-02-17."
            )
        ]

    answers = inquirer.prompt(questions)
    meta = {
        "name": answers.get('name'),
        "description": answers.get("description"),
        "updated_at": answers.get("updated_at")
    }

    return meta

def describe_dataset():
    """
    describe_dataset asks the user to specify some basic info about the dataset
    """
    questions = [
            inquirer.Text(
                'name',
                message="How would you like to name the dataset?"
            ),
            inquirer.Text(
                'description',
                message="What is the dataset about? This will be the description of the dataset."
            )
        ]

    answers = inquirer.prompt(questions)
    meta = {
        "name": answers.get('name', ""),
        "description": answers.get('description', "")
    }

    return meta


def where_is_dataset():
    """
    where_is_dataset asks the user where the dataset is located.
    """
    try:
        folders = []
        for root, dirs, files in os.walk(__CWD__):
            for d in dirs:
                if d not in IGNORED_FOLDERS_AND_FILES:
                    folders.append(
                        os.path.relpath(os.path.join(root, d), ".")
                    )
    except Exception as e:
        logger.error("Can not get a list of folders in current directory.")
        folders = []

    folders = [i for i in folders if not i.startswith(".")]

    if folders:
        questions = [
            inquirer.List(
                'dataset_folder',
                message="Which folder contains the data file?",
                choices=folders
            )
        ]
    else:
        questions = [
            inquirer.Path(
                'dataset_folder',
                message="Which folder will you place the data files?",
                path_type=inquirer.Path.DIRECTORY,
            )
        ]

    answers = inquirer.prompt(questions)
    dataset_folder = answers.get('dataset_folder')

    return dataset_folder


# _FLORA.herb("geonames_timezone").leaves.get("dataset/geonames_timezone.csv").data

@click.group()
def dataherb():
    click.echo("Hello {}".format(os.environ.get('USER', '')))
    click.echo("Welcome to DataHerb.")

@dataherb.command()
def search(keywords, ids):
    fl = Flora()
    click.echo('Search Herbs in DataHerb Flora ...')
    fl.search()

@dataherb.command()
@click.confirmation_option(
    prompt=f"Your current working directory is {__CWD__}\n"
    "The .dataherb folder will be created right here.\n"
    "Are you sure this is the correct path?"
)
def create():

    md = MetaData()

    dataset_basics = describe_dataset()
    print(dataset_basics)
    md.template.update(dataset_basics)

    dataset_folder = where_is_dataset()
    print(
        f"Looking into the folder {dataset_folder} for data files..."
    )

    dataset_files = md.parse_structure(dataset_folder)
    print(
        f"found {dataset_files} in {dataset_folder}"
    )

    for file in dataset_files:
        file_meta = describe_file(file)
        md.append_leaf(os.path.join(dataset_folder,file), file_meta)

    md.create()

    click.echo(
        "The .dataherb folder and metadata.yml file has been created inside \n"
        f"{__CWD__}\n"
        "Please review the metadata.yml file and update other necessary fields of your desire."
    )

if __name__ == "__main__":
    fl = Flora()
    pass
