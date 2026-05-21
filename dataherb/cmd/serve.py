"""
CLI command for serving the flora as a local website.
"""
import sys
from pathlib import Path

import click
from loguru import logger
from mkdocs.commands.serve import serve as _serve

from dataherb.flora import Flora
from dataherb.serve.save_mkdocs import SaveMkDocs
from dataherb.utils.configs import Config

logger.remove()
logger.add(sys.stderr, level="INFO", enqueue=True)


@click.command()
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
@click.option(
    "--dev_addr",
    "-a",
    default="localhost:52125",
    metavar="<IP:PORT>",
    help="Specify the address of the dev server; defaults to localhost:52125",
)
@click.option(
    "--recreate",
    "-r",
    default=False,
    required=False,
    help="Whether to recreate the website. Recreation will delete all the current generated pages and rebuild the whole website.",
)
def serve(flora, workdir, dev_addr, recreate):
    """
    Create a dataherb server and view the flora in your browser.

    :param flora: the path to the flora file. If not given,
        will use the default flora in the configuration.
    :param workdir: the path to the work directory. If not given,
        will use the workdir in the configuration.
    :param dev_addr: the address of the dev server.
    :param recreate: whether to recreate the website.
    """

    if flora is None:
        c = Config()
        flora = c.flora_path

    if workdir is None:
        c = Config()
        workdir = c.workdir

    fl = Flora(flora_path=flora)

    mk = SaveMkDocs(flora=fl, workdir=workdir, folder=".serve")
    mk.save_all(recreate=recreate)

    click.echo(f"Open http://{dev_addr}")
    click.launch(f"http://{dev_addr}")
    _serve(config_file=str(mk.mkdocs_config), dev_addr=dev_addr)
