import csv
import logging
import os
from collections import OrderedDict
from pathlib import Path

import ruamel.yaml
from ruamel.yaml.representer import RoundTripRepresenter

logging.basicConfig()
logger = logging.getLogger("dataherb.parse.model")

IGNORED_FOLDERS_AND_FILES = ['.git', '.dataherb', '.vscode']

# Add representer to ruamel.yaml for OrderedDict
class MyRepresenter(RoundTripRepresenter):
    pass

ruamel.yaml.add_representer(
    OrderedDict, MyRepresenter.represent_dict, representer=MyRepresenter
)
yaml = ruamel.yaml.YAML()
yaml.Representer = MyRepresenter


class MetaData(object):
    def __init__(self):
        self.dataherb_folder = '.dataherb'
        self.metadata_file = 'metadata.yml'
        self.template = OrderedDict({
            "name": "",
            "description": "",
            "contributors": [
                {
                    "name": "",
                    "github": ""
                }
            ],
            "data": [],
            "references": [
                {
                    "name": "",
                    "link": ""
                }
            ]
        })

    def parse_structure(self, folder=None):

        if folder is None:
            folder = '.'

        tree_f = []
        tree_d = []
        for root, dirs, files in os.walk(folder):
            for d in dirs:
                if d not in IGNORED_FOLDERS_AND_FILES:
                    tree_d.append(
                        os.path.relpath(os.path.join(root, d), folder)
                    )
            for f in files:
                tree_f.append(
                    os.path.relpath(os.path.join(root, f), folder)
                )

        self.tree = tree_f

        return self.tree

    def parse_csv(self, csv_file):
        """
        parse_csv parses the csv files for metadata generation
        """

        with open(csv_file, "r") as f:
            reader = csv.reader(f)
            columns = next(reader)

        fields = []
        for col in columns:
            fields.append({
                "name": col,
                "description": ""
            })

        return fields

    def _generate_leaf(self, path, meta_input):

        name = meta_input.get("name", "")
        description = meta_input.get("description", "")
        updated_at = meta_input.get("updated_at", "")

        file_format = path.split(".")[-1]
        if len(file_format) >= 10:
            logger.error(f"The format of file {path} could not be determined!")
            file_format = ""

        file_size = os.stat(path).st_size

        if file_format == "csv":
            fields = self.parse_csv(path)
        else:
            fields = [
                {
                    "name": "",
                    "description": ""
                },
                {
                    "name": "",
                    "description": ""
                }
            ]

        res = {
            "name": name,
            "description": description,
            "path": path,
            "format": file_format,
            "size": file_size,
            "updated_at": updated_at,
            "fields": fields
        }

        return res

    def append_leaf(self, dataset_file, meta_input):

        existing_leaves = self.template["data"]
        existing_leaves.append(
            self._generate_leaf(dataset_file, meta_input)
        )
        self.template.update(data=existing_leaves)

    def create(self):

        # create .dataherb folder
        dataherb_folder = self.dataherb_folder
        try:
            os.mkdir(dataherb_folder)
            logger.info("Created ", dataherb_folder)
        except FileExistsError:
            logger.info(
                dataherb_folder,
                " already exists! Creating metadata.yml file inside."
            )
            pass

        metadata_file = self.metadata_file

        if os.path.isfile(os.path.join(dataherb_folder, metadata_file)):
            logger.error(
                f'File {os.path.join(dataherb_folder, metadata_file)} already exists!'
            )
            raise SystemExit

        with open(os.path.join(dataherb_folder, metadata_file), 'w') as fp:
            documents = yaml.dump(self.template, fp)
