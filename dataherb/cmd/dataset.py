"""
CLI commands that operate on a local dataset (create, upload, validate).
"""
import sys
from pathlib import Path

import click
from datapackage import Package
from loguru import logger

from dataherb.cmd.create import describe_dataset
from dataherb.cmd.sync_git import upload_dataset_to_git
from dataherb.cmd.sync_s3 import upload_dataset_to_s3
from dataherb.core.base import Herb
from dataherb.flora import Flora
from dataherb.parse.model_json import MetaData
from dataherb.parse.utils import STATUS_CODE
from dataherb.utils.configs import Config

logger.remove()
logger.add(sys.stderr, level="INFO", enqueue=True)


@click.command()
@click.argument("path", type=click.Path(exists=True))
@click.option(
    "--flora",
    "-f",
    default=None,
    help=(
        "Specify the path to the flora; " "defaults to default flora in configuration."
    ),
)
def create(path, flora):
    """
    Create metadata for a dataset.

    :param path: path to the dataset folder.
    :param flora: the path to the flora file. If not given,
        will use the default flora in the configuration.
    """
    if isinstance(path, str):
        path = Path(path)

    click.prompt(
        f"Working directory: {path.resolve().absolute()}\n"
        f"A dataherb.json file will be created in {path}.\n"
        "Are you sure this is the correct path?",
        confirmation_prompt=True,
    )

    if flora is None:
        c = Config()
        flora = c.flora_path

    use_existing_dpkg = False

    if (path / "dataherb.json").exists():
        use_existing_dpkg = click.confirm(
            f"A dataherb.json file already exists in {path}. "
            f"Shall we use the existing dataherb.json?",
            default=True,
            show_default=True,
        )

    fl = Flora(flora_path=flora)
    md = MetaData(folder=path)

    if use_existing_dpkg:
        logger.debug("Using existing dataherb.json ...")
        md.load()
    else:
        dataset_basics = describe_dataset()
        print(dataset_basics)
        md.metadata.update(dataset_basics)

        pkg = Package()
        pkg.infer("**/*.csv")
        pkg_descriptor = {"datapackage": pkg.descriptor}

        md.metadata.update(pkg_descriptor)

        if (path / "dataherb.json").exists():
            is_overwrite = click.confirm(
                "Replace the current dataherb.json file?", default=False
            )
            if is_overwrite:
                md.create(overwrite=is_overwrite)

                click.echo(
                    f"The dataherb.json file in folder {path} has been replaced. \n"
                    "Please review the dataherb.json file and update other necessary fields."
                )
            else:
                click.echo("We did nothing.")
                raise SystemExit(0)
        else:
            md.create()
            click.echo(
                "The dataherb.json file has been created inside \n"
                f"{path}\n"
                "Please review the dataherb.json file and update other necessary fields."
            )

    hb = Herb(md.metadata, with_resources=False)
    fl.add(hb)

    click.echo(f"Added {hb.id} into the flora.")


@click.command()
@click.option("--experimental", "-e", default=False, help="Use experimental features")
def upload(experimental):
    """
    Upload dataset in the current folder to the remote destination.
    """
    cwd = Path.cwd()

    is_confirm = click.confirm(
        f"Your current working directory is {cwd}\n"
        "All contents in this folder will be uploaded.\n"
        "Are you sure this is the correct path?",
        default=False,
    )
    if not is_confirm:
        click.echo("Upload aborted.")
        return

    md = MetaData(folder=cwd)
    md.load()

    md_uri = md.metadata["uri"]

    is_upload = click.confirm(
        f"The dataset in the current folder\n"
        f"{cwd}\n"
        f"will be uploaded to {md_uri}",
        default=True,
        show_default=True,
    )

    if not is_upload:
        click.echo("Upload aborted.")
    else:
        click.echo(f"Uploading dataset to {md_uri} ...")
        if md.metadata.get("source") == "s3":
            upload_dataset_to_s3(str(cwd), md_uri)
        elif md.metadata.get("source") == "git":
            upload_dataset_to_git(cwd, md_uri, experimental=experimental)


@click.command()
@click.option("-v", "--verbose", type=str, default="warning")
def validate(verbose):
    """
    Validate the existing metadata for the current dataset.
    """
    cwd = Path.cwd()

    click.secho(
        f"Your current working directory is {cwd}\n"
        "I will look for the dataherb.json file right here.\n",
        bold=True,
    )

    ALL_VERBOSE = ["warning", "error", "all"]
    if verbose not in ALL_VERBOSE:
        raise click.BadParameter(
            f"-v / --verbose must be one of {ALL_VERBOSE}", param_hint="--verbose"
        )

    md = MetaData(folder=cwd)
    try:
        validation_result = md.validate()
    except FileNotFoundError as exc:
        raise click.ClickException(str(exc))

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
    for val in validation_result.get("data", []):
        for val_key, val_val in val.items():
            if (val_val.get("status") == STATUS_CODE["SUCCESS"]) and verbose == "all":
                echo_summary(val_key, val_val, bg="green")
            elif (val_val.get("status") == STATUS_CODE["WARNING"]) and verbose in (
                "warning",
                "all",
            ):
                echo_summary(val_key, val_val, bg="magenta")
            elif (val_val.get("status") == STATUS_CODE["ERROR"]) and verbose in (
                "warning",
                "error",
                "all",
            ):
                echo_summary(val_key, val_val, bg="red")

    click.secho(
        f"The dataherb.json in\n{cwd}\n"
        "has been validated. Please read the summary and fix the errors.",
        bold=True,
    )
