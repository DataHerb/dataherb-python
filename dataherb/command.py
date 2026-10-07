import json
import os
import sys
from pathlib import Path

import click
import git
import yaml
import inquirer
from loguru import logger
from mkdocs.commands.serve import serve as _serve
from rich.console import Console


from dataherb.version import __version__
from dataherb.catalog.config import load_config_defaults
from dataherb.catalog.infer import scaffold
from dataherb.catalog.lint import lint_dataset
from dataherb.catalog.resolve import normalize
from dataherb.catalog.util import load_structured
from dataherb.catalog.validate import errors as schema_errors
from dataherb.cmd.catalog import catalog, status
from dataherb.cmd.create import describe_dataset
from dataherb.cmd.search import HerbTable
from dataherb.cmd.sync_git import remote_git_repo, upload_dataset_to_git
from dataherb.cmd.sync_s3 import upload_dataset_to_s3
from dataherb.core.base import Herb
from dataherb.fetch.remote import get_data_from_url
from dataherb.flora import Flora
from dataherb.parse.model_json import MetaData
from dataherb.serve.save_mkdocs import SaveMkDocs
from dataherb.utils.configs import Config

logger.remove()
logger.add(sys.stderr, level="INFO", enqueue=True)
console = Console()


@click.group(invoke_without_command=True)
@click.pass_context
def dataherb(ctx):
    if ctx.invoked_subcommand is None:
        click.echo("Hello {}".format(os.environ.get("USER", "")))
        click.echo(f"Welcome to DataHerb (version {__version__}).")
    else:
        click.echo("Loading Service: %s" % ctx.invoked_subcommand, err=True)


@dataherb.command()
def version():
    """
    Print out the version of the tool.
    """
    click.echo(f"dataherb version {__version__}")


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
@click.option(
    "--locate/--no-locate",
    "-l/ ",
    default=False,
    help="Locate the folder that contains the dataset, only works for --id mode",
)
def search(flora, id, keywords, full, locate):
    """
    search datasets on DataHerb by keywords or id

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
    create a dataherb server and view the flora in your browser.

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


@dataherb.command()
@click.argument("path", type=click.Path(exists=True, file_okay=False), default=".")
@click.option(
    "--flora",
    "-f",
    default=None,
    help=(
        "Specify the path to the flora; " "defaults to default flora in configuration."
    ),
)
@click.option(
    "--id", "dataset_id", default=None, help="Dataset id; defaults to the folder name."
)
@click.option("--name", default=None, help="Dataset name.")
@click.option(
    "--format",
    "fmt",
    type=click.Choice(["json", "yaml"]),
    default="json",
    show_default=True,
    help="Write dataherb.json or dataherb.yml.",
)
@click.option(
    "--no-input",
    is_flag=True,
    help="Do not ask questions; infer what can be inferred and leave the rest blank.",
)
@click.option(
    "--add-to-flora/--no-add-to-flora",
    default=None,
    help="Add the dataset to the local flora. Defaults to yes when dataherb is configured.",
)
def create(path, flora, dataset_id, name, fmt, no_input, add_to_flora):
    """
    creates metadata for the dataset in PATH (default: current folder)

    Data files (csv, tsv, parquet, json, ndjson) are scanned for columns,
    types and row counts; install duckdb for exact types of every format.
    The result follows the DataHerb v2 metadata spec.
    """
    path = Path(path)
    target = path / ("dataherb.json" if fmt == "json" else "dataherb.yml")
    existing = [
        p for p in (path / "dataherb.json", path / "dataherb.yml") if p.exists()
    ]

    md = scaffold(path, dataset_id=dataset_id, name=name)
    if existing and not no_input:
        if not click.confirm(
            f"{existing[0]} already exists. Replace it?", default=False
        ):
            click.echo("We did nothing.")
            sys.exit()
    elif existing and no_input:
        click.secho(f"{existing[0]} already exists; not overwriting.", fg="red")
        sys.exit(1)

    if not no_input:
        click.echo(f"Describing the dataset in {path.resolve()}")
        md.update(describe_dataset(md))

    if fmt == "json":
        target.write_text(json.dumps(md, indent=4, ensure_ascii=False) + "\n")
    else:
        target.write_text(yaml.safe_dump(md, sort_keys=False, allow_unicode=True))
    n = len(md["datapackage"]["resources"])
    click.echo(
        f"Wrote {target} with {n} resource(s).\n"
        "Review it and fill in what is missing; `dataherb validate` shows the gaps."
    )

    if add_to_flora is None:
        add_to_flora = (Path.home() / ".dataherb" / "config.json").exists()
    if add_to_flora:
        if flora is None:
            flora = Config().flora_path
        fl = Flora(flora_path=flora)
        hb = Herb(md, with_resources=False)
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

    fl = Flora(flora_path=flora)
    herb = fl.herb(herb_id)
    if not herb:
        click.echo(click.style(f"Could not find herb with id {herb_id}", fg="red"))
        click.echo("We did nothing.")
        sys.exit()

    to_remove = click.confirm(f"Remove {herb_id} from the flora?", default=False)
    if to_remove:
        fl.remove(herb_id)
        click.echo(f"Removed {herb_id} from the flora.")
    else:
        click.echo("We did nothing.")


@dataherb.command()
@click.confirmation_option(
    prompt=f"Your current working directory is {Path.cwd()}\n"
    "All contents in this folder will be uploaded.\n"
    "Are you sure this is the correct path?"
)
@click.option("--experimental", "-e", default=False, help="Use experimental features")
def upload(experimental):
    """
    upload dataset in the current folder to the remote destination
    """

    cwd = Path.cwd()
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


@dataherb.command()
@click.argument("path", type=click.Path(exists=True, file_okay=False), default=".")
@click.option(
    "--min-score", type=int, default=None, help="Fail when the quality score is lower."
)
def validate(path, min_score):
    """
    validates the metadata (dataherb.json or dataherb.yml) of the dataset in PATH

    Checks the metadata against the DataHerb v2 schema, checks that every
    listed data file exists, and prints a metadata quality score.
    """
    path = Path(path)
    meta_file = next(
        (
            path / n
            for n in ("dataherb.json", "dataherb.yml", "dataherb.yaml")
            if (path / n).exists()
        ),
        None,
    )
    if meta_file is None:
        click.secho(f"No dataherb.json or dataherb.yml in {path.resolve()}", fg="red")
        sys.exit(1)

    meta = load_structured(meta_file.read_text(), meta_file.name)
    problems = schema_errors("dataset", meta)
    for r in (meta.get("datapackage") or {}).get("resources") or []:
        p = r.get("path")
        if isinstance(p, str) and "://" not in p and not (path / p).exists():
            problems.append(f"resource {r.get('name') or p}: file {p} not found")

    for msg in problems:
        click.secho(f"error: {msg}", fg="red")

    record = normalize(meta, {}, None, {}, load_config_defaults(path))
    quality = lint_dataset(record)
    click.secho(f"Metadata quality: {quality['score']}/100", bold=True)
    for f in quality["findings"]:
        if f["check"] != "reachable":
            click.echo(f"  - {f['message']}")

    if problems or (min_score is not None and quality["score"] < min_score):
        sys.exit(1)
    click.secho(f"{meta_file} is valid.", fg="green")


@dataherb.command()
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
    add herb to flora from a remote source

    :param flora: path to flora
    :param source: source of remote data
    :param uri: uri to the remote dataset metadata file
    """

    if flora is None:
        c = Config()
        flora = c.flora_path

    if not source:
        raise ValueError("Please specify a supported source.")

    if source == "github":
        parsed = remote_git_repo(uri)
        metadata_request = get_data_from_url(parsed["metadata_uri"])

        if not metadata_request.status_code == 200:
            raise Exception(
                "Could not download metadata from remote. status code: {}".format(
                    metadata_request.status_code
                )
            )
        else:
            metadata = metadata_request.json()

        # TODO: save content to file


dataherb.add_command(catalog)
dataherb.add_command(status)
