import os
import click
from dataherb import Flora
import logging
from parse.model import MetaData

__CWD__ = os.getcwd()

logging.basicConfig()
logger = logging.getLogger("dataherb.command")


_FLORA = Flora()

_FLORA.herb("geonames_timezone").leaves.get("dataset/geonames_timezone.csv").data

@click.group()
def dataherb():
    click.echo("Hello {}".format(os.environ.get('USER', '')))
    click.echo("Welcome to DataHerb.")

@dataherb.command()
def search(keywords, ids):
    click.echo('Search Herbs in DataHerb Flora ...')
    _FLORA.search()

@dataherb.command()
@click.confirmation_option(
    prompt=f"Your current working directory is {__CWD__}\n"
    "The .dataherb folder will be created right here.\n"
    "Are you sure this is the correct path?"
)
def create():

    md = MetaData()
    md.create()

    click.echo(
        "The .dataherb folder and metadata.yml file has been created inside \n"
        f"{__CWD__}"
    )
