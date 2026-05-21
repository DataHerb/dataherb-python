"""
CLI commands that operate on a Flora (search, download, add, remove).
"""
import json
import sys
from pathlib import Path

import click
import git
from loguru import logger
from rich.console import Console

from dataherb.cmd.search import HerbTable
from dataherb.cmd.sync_git import remote_git_repo
from dataherb.core.base import Herb
from dataherb.fetch.remote import get_data_from_url
from dataherb.flora import Flora
from dataherb.utils.configs import Config

logger.remove()
logger.add(sys.stderr, level="INFO", enqueue=True)

console = Console()


@click.command()
@click.option(
    "--flora",
    "-f",
    default=None,
    help="Path to the flora file; Defaults to the default flora in the configuration.",
)
@click.option("--id", "-i", required=False, help="The id of the dataset to describe.")
@click.argument("keywords", required=False)
@click.option(
    "--full/--summary", default=False, help="Whether to show the full json result"
)
@click.option(
    "--locate/--no-locate",
    "-l/ ",
    default=False,
    help="Locate the folder that contains the dataset, only works for --id mode",
)
def search(flora, id, keywords, full, locate):
    """
    Search datasets in DataHerb Flora by keywords or id.

    :param flora: the path to the flora file. If not given,
        will use the default flora in the configuration.
    :param id: the id of the dataset to find.
    :param keywords: the keywords to search.
    :param full: whether to show the full json result.
    :param locate: if flag is given, will locate the dataset folder.
    """
    if flora is None:
        c = Config()
        flora = c.flora_path

    fl = Flora(flora_path=flora)
    if not id:
        click.echo("Searching Herbs in DataHerb Flora ...")
        results = fl.search(keywords)
        click.echo(f"Found {len(results)} results")
        if not results:
            click.echo(f"Could not find dataset related to {keywords}")
        else:
            for result in results:
                result_herb = result.get("herb")
                result_metadata = result.get("herb").metadata
                if not full:
                    ht = HerbTable(result_herb)
                    console.rule(title=f"{result_herb.id}", characters="||")
                    console.print(ht.table())
                    console.print(ht.resource_tree())
                else:
                    console.rule(title=f"{result_herb.id}", characters="||")
                    click.secho(f"DataHerb ID: {result_herb.id}")
                    click.echo(json.dumps(result_metadata, indent=2, sort_keys=True))
    else:
        click.echo(f"Fetching Herbs {id} in DataHerb Flora ...")
        result = fl.herb(id)
        if not result:
            click.echo(f"Could not find dataset with id {id}")
        else:
            result_metadata = result.metadata

            if not full:
                ht = HerbTable(result)
                console.rule(title=f"{result.id}", characters="||")
                console.print(ht.table())
                console.print(ht.resource_tree())
            else:
                console.rule(title=f"{result.id}", characters="||")
                click.secho(f"DataHerb ID: {result.id}")
                click.echo(json.dumps(result_metadata, indent=2, sort_keys=True))

            if locate:
                click.launch(str(result.base_path))


@click.command()
@click.argument("id", required=True)
@click.option(
    "--flora",
    "-f",
    default=None,
    help="Specify the path to the flora; defaults to default flora in configuration.",
)
@click.option(
    "--workdir",
    "-w",
    default=None,
    help="Specify the path to the work directory; defaults to the workdir in configuration.",
)
def download(id, flora, workdir):
    """
    Download dataset using id.

    :param id: the id of the dataset to download.
    :param flora: the path to the flora file. If not given,
        will use the default flora in the configuration.
    :param workdir: the path to the work directory. If not given,
        will use the workdir in the configuration.
    """

    if flora is None:
        c = Config()
        flora = c.flora_path

    if workdir is None:
        c = Config()
        workdir = c.workdir

    fl = Flora(flora_path=flora)
    click.echo(f"Fetching Herbs {id} in DataHerb Flora ...")
    result = fl.herb(id)
    if not result:
        click.echo(f"Could not find dataset with id {id}")
    else:
        result_metadata = result.metadata
        result_uri = result_metadata.get("uri")
        result_id = result_metadata.get("id")
        dest_folder = Path(workdir) / result_id
        click.echo(
            f'Downloading DataHerb ID: {result_metadata.get("id")} into {dest_folder}'
        )
        if dest_folder.exists():
            click.echo(f"Can not download dataset to {dest_folder}: folder exists.\n")

            is_pull = click.confirm(f"Would you like to pull from remote?")
            if is_pull:
                repo = git.Repo(dest_folder)
                repo.git.pull()
            else:
                click.echo(
                    f"Please go to the folder {dest_folder} and sync your repo manually."
                )
        else:
            dest_folder.mkdir(parents=True, exist_ok=False)
            repo = git.repo.base.Repo.clone_from(result_uri, to_path=dest_folder)


@click.command()
@click.option(
    "--flora",
    "-f",
    default=None,
    help="Specify the path to the flora; defaults to default flora in configuration.",
)
@click.option(
    "--source",
    "-s",
    type=click.Choice(["github"], case_sensitive=False),
    default="github",
    help="Source of remote data.",
)
@click.argument("uri", required=True)
def add(flora, source, uri):
    """
    Add herb to flora from a remote source.

    :param flora: path to flora
    :param source: source of remote data
    :param uri: uri to the remote dataset metadata file
    """

    if flora is None:
        c = Config()
        flora = c.flora_path

    if not source:
        raise click.UsageError("Please specify a supported source.")

    if source == "github":
        parsed = remote_git_repo(uri)
        metadata_request = get_data_from_url(parsed["metadata_uri"])

        if metadata_request.status_code != 200:
            raise click.ClickException(
                "Could not download metadata from remote. status code: {}".format(
                    metadata_request.status_code
                )
            )

        metadata = metadata_request.json()

    fl = Flora(flora_path=flora)
    hb = Herb(metadata, with_resources=False)
    fl.add(hb)
    click.echo(f"Added {hb.id} into the flora.")


@click.command()
@click.option(
    "--flora",
    "-f",
    default=None,
    help="Specify the path to the flora; defaults to default flora in configuration.",
)
@click.argument("herb_id", required=True)
def remove(flora, herb_id):
    """
    Remove herb from flora.
    """
    if flora is None:
        c = Config()
        flora = c.flora_path

    fl = Flora(flora_path=flora)
    herb = fl.herb(herb_id)
    if not herb:
        click.echo(click.style(f"Could not find herb with id {herb_id}", fg="red"))
        click.echo("We did nothing.")
        raise SystemExit(0)

    to_remove = click.confirm(f"Remove {herb_id} from the flora?", default=False)
    if to_remove:
        fl.remove(herb_id)
        click.echo(f"Removed {herb_id} from the flora.")
    else:
        click.echo("We did nothing.")
