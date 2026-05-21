"""
CLI command for configuring dataherb.
"""
import json
import sys
from pathlib import Path

import click
import inquirer
from loguru import logger

from dataherb.utils.configs import Config

logger.remove()
logger.add(sys.stderr, level="INFO", enqueue=True)


@click.command()
@click.option(
    "--show/--no-show", "-s/ ", default=False, help="Show the current configuration"
)
@click.option(
    "--locate/--no-locate",
    "-l/ ",
    default=False,
    help="Locate the folder that contains the configuration",
)
def configure(show, locate):
    """
    Configure dataherb; inspect, or locate the current configurations.

    :param show: if flag is given, will show the current configuration instead of starting
        the configuration process.
    :param locate: if flag is given, will locate the configuration folder
        and open in filesystem.
    """

    home = Path.home()
    config_path = home / ".dataherb" / "config.json"

    if locate:
        click.launch(config_path.parent)
    elif not show:
        if config_path.exists():
            is_overwite = click.confirm(
                click.style(
                    f"Config file ({config_path}) already exists. Overwrite?", fg="red"
                ),
                default=False,
            )
            if is_overwite:
                click.echo(click.style("Overwriting config file...", fg="red"))
            else:
                click.echo("Skipping...")
                raise SystemExit(0)

        if not config_path.parent.exists():
            config_path.parent.mkdir(parents=True)

        ###############
        # Ask questions
        ###############
        questions = [
            inquirer.Path(
                "workdir",
                message="Where should I put all the datasets and flora database? An empty folder is recommended.",
                # path_type=inquirer.Path.DIRECTORY,
                normalize_to_absolute_path=True,
            ),
            inquirer.Text(
                "default_flora",
                message="How would you name the default flora? Please keep the default value if this is not clear to you.",
                default="flora",
            ),
        ]

        answers = inquirer.prompt(questions)

        config = {
            "workdir": answers.get("workdir"),
            "default": {
                "flora": answers.get("default_flora"),
                "aggregrated": False,  # if false, we will use folders for each herb.
            },
        }

        flora_path_workdir = answers.get("workdir", "")
        if flora_path_workdir.startswith("~"):
            home = Path.home()
            flora_path_workdir = str(home / flora_path_workdir[2:])

        flora_path = (
            Path(flora_path_workdir) / "flora" / f"{answers.get('default_flora')}"
        )
        if not flora_path.exists():
            click.secho(
                f"{flora_path} doesn't exist. Creating {flora_path}...", fg="red"
            )
            flora_path.mkdir(parents=True)
        else:
            click.secho(f"{flora_path} exists, using the folder directly.", fg="green")

        logger.debug(f"config: {config}")

        with open(config_path, "w") as f:
            json.dump(config, f, indent=4)

        click.secho(f"The dataherb config has been saved to {config_path}!", fg="green")
    else:
        if not config_path.exists():
            click.secho(f"Config file ({config_path}) doesn't exist.", fg="red")
        else:
            c = Config()
            click.secho(f"The current config for dataherb is:")
            click.secho(
                json.dumps(c.config, indent=2, sort_keys=True, ensure_ascii=False)
            )
            click.secho(f"The above config is extracted from {config_path}")
