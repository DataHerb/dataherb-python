from logging import log
import os
import sys
from dataherb.cmd.create import describe_dataset, describe_file, where_is_dataset
from dataherb.cmd.configs import load_dataherb_config
from collections import OrderedDict
from pathlib import Path
from datapackage import Package

import click
import git
from loguru import logger

from dataherb.flora import Flora
from dataherb.parse.model_json import STATUS_CODE, MetaData

__CWD__ = os.getcwd()

CONFIG = load_dataherb_config()
logger.debug(CONFIG)
WD = CONFIG['workdir']
which_flora = CONFIG.get("default", {}).get("flora")
if which_flora:
    which_flora = str(Path(WD)/"flora"/Path(which_flora + ".json"))
    logger.debug(f"Using flora path: {which_flora}")
    if not os.path.exists(which_flora):
        raise Exception(f"flora config {which_flora} does not exist")


@click.group(invoke_without_command=True)
@click.pass_context
def dataherb(ctx):
    if ctx.invoked_subcommand is None:
        click.echo("Hello {}".format(os.environ.get("USER", "")))
        click.echo("Welcome to DataHerb.")
    else:
        click.echo("Loading Service: %s" % ctx.invoked_subcommand)


@dataherb.command()
@click.argument("keywords", required=False)
@click.option("--id", "-i", required=False)
@click.option("--flora", "-f", default=which_flora)
def search(flora, id=None, keywords=None):
    """
    search datasets on DataHerb by keywords or id
    """
    SHOW_KEYS = ["name", "description", "contributors"]
    fl = Flora(flora=flora)
    if not id:
        click.echo("Searching Herbs in DataHerb Flora ...")
        results = fl.search(keywords)
        click.echo(f"Found {len(results)} results")
        if not results:
            click.echo(f"Could not find dataset related to {keywords}")
        else:
            for result in results:
                result_metadata = result.get("herb").metadata
                click.echo(f'DataHerb ID: {result_metadata.get("id")}')
                click.echo(result_metadata)
    else:
        click.echo(f"Fetching Herbs {id} in DataHerb Flora ...")
        result = fl.herb(id)
        if not result:
            click.echo(f"Could not find dataset with id {id}")
        else:
            result_metadata = result.metadata
            click.echo(f'DataHerb ID: {result_metadata.get("id")}')
            click.echo(result_metadata)


@dataherb.command()
@click.argument("id", required=True)
@click.option("--flora", "-f", default=which_flora)
def download(id, flora):
    """
    download dataset using id
    """

    fl = Flora(flora=flora)
    click.echo(f"Fetching Herbs {id} in DataHerb Flora ...")
    result = fl.herb(id)
    if not result:
        click.echo(f"Could not find dataset with id {id}")
    else:
        result_metadata = result.metadata
        click.echo(f'Downloading DataHerb ID: {result_metadata.get("id")}')
        result_uri = result_metadata.get("uri")
        result_id = result_metadata.get("id")
        dest_folder = str(Path(WD) / result_id)
        if os.path.exists(dest_folder):
            click.echo(f"Can not download dataset to {dest_folder}: folder exists.")
        else:
            # dest_folder_parent = f"./{result_repository.split('/')[0]}"
            os.makedirs(dest_folder)
            git.Git(dest_folder).clone(result_uri)


@dataherb.command()
@click.confirmation_option(
    prompt=f"Your current working directory is {__CWD__}\n"
    "A datapackage.json file will be created right here.\n"
    "Are you sure this is the correct path?"
)
def create():
    """
    creates metadata for current dataset
    """

    md = MetaData(folder=__CWD__)

    dataset_basics = describe_dataset()
    print(dataset_basics)
    md.metadata.update(dataset_basics)

    pkg = Package()
    pkg.infer('**/*.csv')
    pkg_descriptor = {
        "datapackage": pkg.descriptor
    }

    md.metadata.update(pkg_descriptor)

    # dataset_folder = where_is_dataset(__CWD__)
    # print(f"Looking into the folder {dataset_folder} for data files...")

    md.create()

    click.echo(
        "The datapackage.json file has been created inside \n"
        f"{__CWD__}\n"
        "Please review the datapackage.json file and update other necessary fields."
    )


@dataherb.command()
@click.option("-v", "--verbose", type=str, default="warning")
def validate(verbose):
    """
    validates the existing metadata for current dataset
    """

    click.secho(
        f"Your current working directory is {__CWD__}\n"
        "I will look for the .dataherb folder right here.\n",
        bold=True,
    )

    ALL_VERBOSE = ["warning", "error", "all"]
    if verbose not in ALL_VERBOSE:
        logger.error(f"-v or --verbose can only take one of {ALL_VERBOSE}")

    md = MetaData()

    validate = md.validate()

    def echo_summary(key, value_dict, bg=None, fg=None):
        if bg is None:
            bg = "black"
        if fg is None:
            fg = "white"
        return click.secho(
            f'  {key}: {value_dict.get("value")}\n'
            f'    STATUS: {value_dict.get("status")};\n'
            f'    MESSAGE: {value_dict.get("message")}',
            bg=bg,
            fg=fg,
        )

    click.secho("Summary: validating metadata:\n- data:", bold=True)
    for val in validate.get("data"):
        for val_key, val_val in val.items():
            if (val_val.get("status") == STATUS_CODE["SUCCESS"]) and (verbose == "all"):
                echo_summary(val_key, val_val, bg="green")
            elif (val_val.get("status") == STATUS_CODE["WARNING"]) and (
                verbose == "warning"
            ):
                echo_summary(val_key, val_val, bg="magenta")
            elif (val_val.get("status") == STATUS_CODE["ERROR"]) and (
                verbose in ["warning", "error"]
            ):
                echo_summary(val_key, val_val, bg="red")

    click.secho(
        "The .dataherb folder and metadata.yml file \n"
        f"{__CWD__}\n"
        " has been validated. Please read the summary and fix the errors.",
        bold=True,
    )


if __name__ == "__main__":
    fl = Flora()
    pass
