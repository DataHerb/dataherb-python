import json
from distutils.dir_util import copy_tree
import os, sys
import click
from pathlib import Path
import time
import yaml

from dataherb.serve.models import SaveModel
from dataherb.serve.mkdocs_templates import site_config as _site_config
from dataherb.serve.mkdocs_templates import index_template as _index_template

from loguru import logger
from slugify import slugify

logger.remove()
logger.add(sys.stderr, level="INFO", enqueue=True)


class SaveMkDocs(SaveModel):
    """
    SaveMkDocs saves the dataset files from source as MkDocs files
    """

    def __init__(self, flora, workdir):

        super().__init__(flora, workdir)

    @staticmethod
    def _generate_markdown_list_meta(dic_lists, name) -> str:
        """
        _markdown_metadata_entry
        """

        if dic_lists:
            md_mkdocs = f"{name}:"
            for l in dic_lists:
                md_mkdocs = md_mkdocs + f'\n  - "{l}"'
            md_mkdocs = md_mkdocs + "\n"
        else:
            md_mkdocs = ""

        return md_mkdocs

    def save_one_markdown(self, herb, path):
        """
        save_one_markdown generates a markdown file
        """

        logger.info(f"Will save {herb.id} to {path}")

        herb_metadata = herb.metadata.copy()
        herb_metadata["title"] = herb_metadata.get("name")
        md_meta = yaml.dump(herb_metadata)

        metadata_mkdocs = f"---\n"
        metadata_mkdocs += md_meta
        metadata_mkdocs += "---\n  "

        with open(path, "w") as fp:
            fp.write(metadata_mkdocs)

        logger.info(f"Saved {herb_metadata} to {path}")

    def save_one_markdown_alt(self, herb, path):
        """
        save_one_markdown generates a markdown file
        """

        logger.info(f"Will save {herb.id} to {path}")

        herb_metadata = herb.metadata

        # generate tilte, description, keywords, and categories
        metadata_title = herb_metadata.get("name")
        metadata_description = herb_metadata.get("description")
        metadata_tags = herb_metadata.get("tags")
        metadata_category = herb_metadata.get("category")

        keywords_mkdocs = self._generate_markdown_list_meta(metadata_tags, "keywords")

        metadata_mkdocs = f'---\ntitle: "{metadata_title}"\n'
        if metadata_description:
            metadata_mkdocs = (
                metadata_mkdocs + f'description: "{metadata_description}"\n'
            )
        if keywords_mkdocs:
            metadata_mkdocs = metadata_mkdocs + keywords_mkdocs
        if metadata_category:
            categories_mkdocs = f"category: {metadata_category}"
            metadata_mkdocs = metadata_mkdocs + categories_mkdocs

        # end the metadata region
        metadata_mkdocs = metadata_mkdocs + "---\n  "

        with open(path, "w") as fp:
            fp.write(metadata_mkdocs)

        logger.info(f"Saved {herb_metadata} to {path}")

    def create_mkdocs_theme(self):
        """copies the prepared theme to the serve dir"""

        mkdocs_folder = Path(self.workdir) / "serve"

        mkdocs_template_path = Path(__file__).parent / "mkdocs_template"

        copy_tree(str(mkdocs_template_path), str(mkdocs_folder))

    def create_mkdocs_yaml(self):
        """creates mkdocs.yaml from mkdocs_templates.py"""

        mkdocs_folder = Path(self.workdir) / "serve"
        mkdocs_yaml_path = mkdocs_folder / "mkdocs.yml"

        with open(mkdocs_yaml_path, "w") as fp:
            fp.write(_site_config)

    def create_mkdocs_index(self):
        """creates herbs/index.md from mkdocs_templates.py"""

        mkdocs_folder = Path(self.workdir) / "serve"
        mkdocs_index_path = mkdocs_folder / "herbs" / "index.md"

        with open(mkdocs_index_path, "w") as fp:
            fp.write(_index_template)

    def save_all(self, recreate=False) -> None:
        """
        save_all saves all files necessary
        """

        # attach working directory to all paths
        md_folder = Path(self.workdir) / "serve" / "herbs"

        # create folders if necessary
        if md_folder.exists():
            if not recreate:
                is_remove = click.confirm(
                    f"{md_folder} exists, remove it and create new?",
                    default=True,
                    show_default=True,
                )
            else:
                is_remove = True

            if is_remove:
                cache_folder = md_folder.parent / "cache"
                if cache_folder.exists():
                    pass
                else:
                    cache_folder.mkdir(parents=True)
                md_folder.rename(cache_folder / f"serve.{int(time.time())}")
                md_folder.mkdir(parents=True)
        else:
            md_folder.mkdir(parents=True)

        for herb in self.flora.flora:
            herb_id = slugify(herb.id)

            herb_md_path = os.path.join(md_folder, f"{herb_id}.md")
            # generate markdown files
            self.save_one_markdown(herb, herb_md_path)

        self.create_mkdocs_theme()


if __name__ == "__main__":

    pass
