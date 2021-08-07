import json
import os
import sys
from pathlib import Path

import click
import git
import inquirer
from datapackage import Package
from loguru import logger
from mkdocs.commands.serve import serve as _serve
from rich.console import Console

from dataherb.cmd.create import describe_dataset
from dataherb.cmd.search import HerbTable
from dataherb.cmd.sync_git import upload_dataset_to_git
from dataherb.cmd.sync_s3 import upload_dataset_to_s3
from dataherb.core.base import Herb
from dataherb.flora import Flora
from dataherb.parse.model_json import STATUS_CODE, MetaData
from dataherb.serve.save_mkdocs import SaveMkDocs
from dataherb.utils.configs import Config

logger.remove()
logger.add(sys.stderr, level="INFO", enqueue=True)
console = Console()


__CWD__ = os.getcwd()


@click.group(invoke_without_command=True)
@click.pass_context
def dataherb(ctx):
    if ctx.invoked_subcommand is None:
        click.echo("Hello {}".format(os.environ.get("USER", "")))
        click.echo("Welcome to DataHerb.")
    else:
        # click.echo("Loading Service: %s" % ctx.invoked_subcommand)
        pass


@dataherb.command()
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
    Configure dataherb; inspect, or lcoate the current configurations.
    """

    home = Path.home()
    config_path = home / ".dataherb" / "config.json"

    if not show:
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
                sys.exit(0)

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
            "default": {"flora": answers.get("default_flora")},
        }

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

    if locate:
        click.launch(str(config_path.parent))


@dataherb.command()
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
def search(flora, id, keywords, full):
    """
    search datasets on DataHerb by keywords or id
    """
    if flora is None:
        c = Config()
        flora = c.flora_path

    fl = Flora(flora=flora)
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


@dataherb.command()
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
    create a dataherb server and view the flora in your browser
    """

    if flora is None:
        c = Config()
        flora = c.flora_path

    if workdir is None:
        c = Config()
        workdir = c.workdir

    fl = Flora(flora=flora)
    mk = SaveMkDocs(flora=fl, workdir=workdir)
    mk.save_all(recreate=recreate)

    mkdocs_config = str(Path(workdir) / "serve" / "mkdocs.yml")

    click.echo(f"Open http://{dev_addr}")
    click.launch(f"http://{dev_addr}")
    _serve(config_file=mkdocs_config, dev_addr=dev_addr)


@dataherb.command()
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
    Download dataset using id
    """

    if flora is None:
        c = Config()
        flora = c.flora_path

    if workdir is None:
        c = Config()
        workdir = c.workdir

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
        dest_folder = str(Path(workdir) / result_id)
        if os.path.exists(dest_folder):
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
            # dest_folder_parent = f"./{result_repository.split('/')[0]}"
            os.makedirs(dest_folder)
            repo = git.repo.base.Repo.clone_from(result_uri, to_path=dest_folder)
            # git.Git(dest_folder).clone(result_uri)


@dataherb.command()
@click.confirmation_option(
    prompt=f"Your current working directory is {__CWD__}\n"
    "A dataherb.json file will be created right here.\n"
    "Are you sure this is the correct path?"
)
@click.option(
    "--flora",
    "-f",
    default=None,
    help="Specify the path to the flora; defaults to default flora in configuration.",
)
def create(flora):
    """
    creates metadata for current dataset
    """
    if flora is None:
        c = Config()
        flora = c.flora_path

    use_existing_dpkg = False

    if (Path(__CWD__) / "dataherb.json").exists():
        use_existing_dpkg = click.confirm(
            f"A dataherb.json file already exists in {__CWD__}. "
            f"Shall we use the existing dataherb.json?",
            default=True,
            show_default=True,
        )

    fl = Flora(flora=flora)
    md = MetaData(folder=__CWD__)

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

        if (Path(__CWD__) / "dataherb.json").exists():
            is_overwrite = click.confirm(
                "Replace the current dataherb.json file?", default=False
            )
            if is_overwrite:
                md.create(overwrite=is_overwrite)

                click.echo(
                    f"The dataherb.json file in folder {__CWD__} has been replaced. \n"
                    "Please review the dataherb.json file and update other necessary fields."
                )
            else:
                click.echo("We did nothing.")
                sys.exit()
        else:
            md.create()
            click.echo(
                "The dataherb.json file has been created inside \n"
                f"{__CWD__}\n"
                "Please review the dataherb.json file and update other necessary fields."
            )

    hb = Herb(md.metadata, with_resources=False)
    fl.add(hb)

    click.echo(f"Added {hb.id} into the flora.")


@dataherb.command()
@click.option(
    "--flora",
    "-f",
    default=None,
    help="Specify the path to the flora; defaults to default flora in configuration.",
)
@click.argument("herb_id", required=True)
def remove(flora, herb_id):
    """
    remove herb from flora
    """
    if flora is None:
        c = Config()
        flora = c.flora_path

    fl = Flora(flora=flora)
    herb = fl.herb(herb_id)
    if not herb:
        click.echo(click.style(f"Could not find herb with id {herb_id}", fg="red"))
        click.echo("We did nothing.")
        sys.exit()

    to_remove = click.confirm(f"Remove {herb_id} from the flora?", default=False)
    if to_remove:
        fl.remove(herb_id)
        click.echo(f"Removed {herb_id} into the flora.")
    else:
        click.echo("We did nothing.")


@dataherb.command()
@click.confirmation_option(
    prompt=f"Your current working directory is {__CWD__}\n"
    "All contents in this folder will be uploaded.\n"
    "Are you sure this is the correct path?"
)
@click.option("--experimental", "-e", default=False, help="Use experimental features")
def upload(experimental):
    """
    upload dataset in the current folder to the remote destination
    """

    md = MetaData(folder=__CWD__)
    md.load()

    md_uri = md.metadata["uri"]

    is_upload = click.confirm(
        f"The dataset in the current folder\n"
        f"{__CWD__}\n"
        f"will be uploaded to {md_uri}",
        default=True,
        show_default=True,
    )

    if not is_upload:
        click.echo("Upload aborted.")
    else:
        click.echo(f"Uploading dataset to {md_uri} ...")
        if md.metadata.get("source") == "s3":
            upload_dataset_to_s3(__CWD__, md_uri)
        elif md.metadata.get("source") == "git":
            upload_dataset_to_git(__CWD__, md_uri, experimental=experimental)


@dataherb.command()
@click.option("-v", "--verbose", type=str, default="warning")
def validate(verbose):
    """
    WIP: validates the existing metadata for current dataset
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
