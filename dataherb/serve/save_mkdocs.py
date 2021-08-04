import json
import os
import click
from pathlib import Path
import time

from dataherb.serve.models import SaveModel

from loguru import logger
from slugify import slugify


class SaveMkDocs(SaveModel):
    """
    SaveMkDocs saves the dataset files from source as MkDocs files
    """

    def __init__(
        self,
        flora,
        workdir
    ):

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

        herb_metadata = herb.metadata

        # generate tilte, description, keywords, and categories
        metadata_title = herb_metadata.get("name")
        metadata_description = herb_metadata.get("description")
        metadata_tags = herb_metadata.get("tags")
        metadata_category = herb_metadata.get("category")

        keywords_mkdocs = self._generate_markdown_list_meta(metadata_tags, "keywords")

        metadata_mkdocs = f'---\ntitle: "{metadata_title}"\n'
        if metadata_description:
            metadata_mkdocs = metadata_mkdocs + f'description: "{metadata_description}"\n'
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

    def save_all(self) -> None:
        """
        save_all saves all files necessary
        """

        # attach working directory to all paths
        md_folder = Path(self.workdir) / "serve" / "herbs"

        # create folders if necessary
        if md_folder.exists():
            is_remove = click.confirm(
                f"{md_folder} exists, remove it and create new?",
                default=True,
                show_default=True
            )
            if is_remove:
                cache_folder = md_folder.parent / "cache"
                if cache_folder.exists():
                    pass
                else:
                    cache_folder.mkdir(parents=True)
                md_folder.rename(
                    cache_folder / f"serve.{int(time.time())}"
                )
        else:
            md_folder.mkdir()


        for herb in self.flora.flora:
            herb_id = slugify(herb.id)

            herb_md_path = os.path.join(md_folder, f"{herb_id}.md")
            # generate markdown files
            self.save_one_markdown(herb, herb_md_path)


if __name__ == "__main__":

    pass