"""
DataHerb CLI entry point.

All command implementations live in submodules under ``dataherb/cmd/``.
This module only wires the Click group together so that the entry-point
console script ``dataherb`` resolves to a single, well-defined group.
"""
import os
import sys

import click
from loguru import logger

from dataherb.version import __version__

# Command modules
from dataherb.cmd.configure import configure
from dataherb.cmd.dataset import create, upload, validate
from dataherb.cmd.flora import add, download, remove, search
from dataherb.cmd.serve import serve

logger.remove()
logger.add(sys.stderr, level="INFO", enqueue=True)


@click.group(invoke_without_command=True)
@click.pass_context
def dataherb(ctx):
    if ctx.invoked_subcommand is None:
        click.echo("Hello {}".format(os.environ.get("USER", "")))
        click.echo(f"Welcome to DataHerb (version {__version__}).")
    else:
        click.echo("Loading Service: %s" % ctx.invoked_subcommand)


@dataherb.command()
def version():
    """
    Print out the version of the tool.
    """
    click.echo(f"dataherb version {__version__}")


# Register commands from submodules
dataherb.add_command(configure)
dataherb.add_command(search)
dataherb.add_command(download)
dataherb.add_command(add)
dataherb.add_command(remove)
dataherb.add_command(create)
dataherb.add_command(upload)
dataherb.add_command(validate)
dataherb.add_command(serve)

