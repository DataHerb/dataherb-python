import csv
import os, sys
from collections import OrderedDict
from pathlib import Path

import ruamel.yaml
from loguru import logger
from ruamel.yaml.representer import RoundTripRepresenter

logger.remove()
logger.add(sys.stderr, level="INFO", enqueue=True)

IGNORED_FOLDERS_AND_FILES = [".git", ".dataherb", ".vscode"]

# Add representer to ruamel.yaml for OrderedDict
class MyRepresenter(RoundTripRepresenter):
    pass


ruamel.yaml.add_representer(
    OrderedDict, MyRepresenter.represent_dict, representer=MyRepresenter
)
yaml = ruamel.yaml.YAML()
yaml.Representer = MyRepresenter

MESSAGE_CODE = {
    "MISSING": lambda x: f"{x} is missing",
    "FILE_NOT_FOUND": lambda x: f"{x} was not found",
    "FILE_FOUND": lambda x: f"{x} was found",
    "EXISTS": lambda x: f"{x} exists",
    "FREE_MESSAGE": lambda x: f"{x}",
}

STATUS_CODE = {
    "UNKNOWN": "unknown",
    "SUCCESS": "success",
    "WARNING": "warning",
    "ERROR": "error",
}


class MetaData(object):
    def __init__(self):
        self.dataherb_folder = ".dataherb"
        self.metadata_file = "metadata.yml"
        self.template = OrderedDict(
            {
                "name": "",
                "description": "",
                "contributors": [{"name": "", "github": ""}],
                "data": [],
                "references": [{"name": "", "link": ""}],
            }
        )

    def parse_structure(self, folder=None):

        if folder is None:
            folder = "."

        tree_f = []
        tree_d = []
        for root, dirs, files in os.walk(folder):
            for d in dirs:
                if d not in IGNORED_FOLDERS_AND_FILES:
                    tree_d.append(os.path.relpath(os.path.join(root, d), folder))
            for f in files:
                tree_f.append(os.path.relpath(os.path.join(root, f), folder))

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
            fields.append({"name": col, "description": ""})

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
            fields = [{"name": "", "description": ""}, {"name": "", "description": ""}]

        res = {
            "name": name,
            "description": description,
            "path": path,
            "format": file_format,
            "size": file_size,
            "updated_at": updated_at,
            "fields": fields,
        }

        return res

    def append_leaf(self, dataset_file, meta_input):

        existing_leaves = self.template["data"]
        existing_leaves.append(self._generate_leaf(dataset_file, meta_input))
        self.template.update(data=existing_leaves)

    def _parse_leaves(self, loaded_meta):
        """_parse_leaf loads the leaves from the metadata."""

        existing_leaves = loaded_meta["data"]

        return existing_leaves

    def create(self):

        # create .dataherb folder
        dataherb_folder = self.dataherb_folder
        try:
            os.mkdir(dataherb_folder)
            logger.info("Created ", dataherb_folder)
        except FileExistsError:
            logger.info(
                dataherb_folder, " already exists! Creating metadata.yml file inside."
            )
            pass

        metadata_file = self.metadata_file

        if os.path.isfile(os.path.join(dataherb_folder, metadata_file)):
            logger.error(
                f"File {os.path.join(dataherb_folder, metadata_file)} already exists!"
            )
            raise SystemExit

        with open(os.path.join(dataherb_folder, metadata_file), "w") as fp:
            documents = yaml.dump(self.template, fp)

    def validate(self):
        """validate the existing metadata file"""

        dataherb_folder = self.dataherb_folder
        metadata_file = self.metadata_file
        summary = {}

        try:
            if not os.path.exists(dataherb_folder):
                logger.error(f"Folder {dataherb_folder} does'nt exists!")
                raise Exception(f"Path {dataherb_folder} doesn't exist!")
            if not os.path.isfile(os.path.join(dataherb_folder, metadata_file)):
                logger.error(
                    f"File {os.path.join(dataherb_folder, metadata_file)} doesn'nt exists!"
                )
                raise SystemExit

            with open(os.path.join(dataherb_folder, metadata_file), "r") as fp:
                documents = yaml.load(fp)

            logger.info("loaded metadata ", dataherb_folder)
        except FileExistsError:
            logger.info(
                dataherb_folder, " already exists! Creating metadata.yml file inside."
            )
            pass

        data = self._parse_leaves(documents)

        data_summary = summary.get("data", [])

        leaf_validation = LeafValidation()
        for d in data:
            data_summary.append(leaf_validation.summary(d))

        summary["data"] = data_summary

        return summary


class LeafValidation:
    def __init__(self):
        self.description = "Validate a Leaf in in Herb"

    def summary(self, d):
        summary = {
            "path": self._validate__path(d),
            "format": self._validate__format(d),
            "description": self._validate__description(d),
            "size": self._validate__size(d),
            "fields": self._validate__fields(d),
        }
        return summary

    @staticmethod
    def _validate__path(d):
        """
        _validate__path checks if the file specified in metadata exists and report.

        :param d: one data entry in metadata loaded as dictionary
        :type d: dict
        """
        data_summary_d_path = {}
        data_summary_d_path["value"] = d.get("path")
        if not d.get("path"):
            data_summary_d_path["message"] = MESSAGE_CODE["MISSING"]("path")
            data_summary_d_path["status"] = STATUS_CODE["ERROR"]
        else:
            if not os.path.isfile(d.get("path")):
                data_summary_d_path["message"] = MESSAGE_CODE["FILE_NOT_FOUND"](
                    d.get("path")
                )
                data_summary_d_path["status"] = STATUS_CODE["ERROR"]
            else:
                data_summary_d_path["status"] = STATUS_CODE["SUCCESS"]
                data_summary_d_path["message"] = MESSAGE_CODE["FILE_FOUND"](
                    d.get("path")
                )

        return data_summary_d_path

    @staticmethod
    def _validate__format(d):
        """
        _validate__format checks if the format specified in metadata exists and report.

        :param d: one data entry in metadata loaded as dictionary
        :type d: dict
        """
        key = "format"
        data_summary_d_format = {}
        data_summary_d_format["value"] = d.get(key)
        if not d.get(key):
            data_summary_d_format["message"] = MESSAGE_CODE["MISSING"](key)
            data_summary_d_format["status"] = STATUS_CODE["ERROR"]
        else:
            data_summary_d_format["status"] = STATUS_CODE["SUCCESS"]
            data_summary_d_format["message"] = MESSAGE_CODE["EXISTS"](d.get(key))

        return data_summary_d_format

    @staticmethod
    def _validate__description(d):
        """
        _validate__description checks if the description of file in metadata exists and report.

        :param d: one data entry in metadata loaded as dictionary
        :type d: dict
        """
        key = "description"
        data_summary_d_description = {}
        data_summary_d_description["value"] = d.get(key)
        if not d.get(key):
            data_summary_d_description["message"] = MESSAGE_CODE["MISSING"](key)
            data_summary_d_description["status"] = STATUS_CODE["WARNING"]
        else:
            data_summary_d_description["status"] = STATUS_CODE["SUCCESS"]
            data_summary_d_description["message"] = MESSAGE_CODE["EXISTS"](d.get(key))

        return data_summary_d_description

    @staticmethod
    def _validate__size(d):
        """
        _validate__size checks if the size of file in metadata exists and report.

        :param d: one data entry in metadata loaded as dictionary
        :type d: dict
        """
        key = "size"
        data_summary_d_size = {}
        data_summary_d_size["value"] = d.get(key)
        if not d.get(key):
            data_summary_d_size["message"] = MESSAGE_CODE["MISSING"](key)
            data_summary_d_size["status"] = STATUS_CODE["WARNING"]
        else:
            data_summary_d_size["status"] = STATUS_CODE["SUCCESS"]
            data_summary_d_size["message"] = MESSAGE_CODE["EXISTS"](d.get(key))

        return data_summary_d_size

    @staticmethod
    def _validate__fields(d):
        """
        _validate__fields checks if the fields of file in metadata exists and report.

        :param d: one data entry in metadata loaded as dictionary
        :type d: dict
        """
        key = "fields"
        data_summary_d_fields = {}
        data_summary_d_fields["value"] = f"{len(d.get(key))} fields in total"
        if not d.get(key):
            data_summary_d_fields["message"] = MESSAGE_CODE["MISSING"](key)
            data_summary_d_fields["status"] = STATUS_CODE["WARNING"]
        else:
            name_missing_counter = 0
            description_missing_counter = 0
            for field in d.get(key):
                if not field.get("name"):
                    name_missing_counter += 1
                if not field.get("description"):
                    description_missing_counter += 1
            if (name_missing_counter == 0) and (description_missing_counter == 0):
                data_summary_d_fields["status"] = STATUS_CODE["SUCCESS"]
                data_summary_d_fields["message"] = MESSAGE_CODE["FREE_MESSAGE"](
                    f"{len(d.get(key))} fields: all names and descriptions filled in."
                )
            elif name_missing_counter > 0:
                data_summary_d_fields["status"] = STATUS_CODE["ERROR"]
                data_summary_d_fields["message"] = MESSAGE_CODE["FREE_MESSAGE"](
                    f"{len(d.get(key))} fields: "
                    f"{len(name_missing_counter)} names missing; "
                    f"{len(description_missing_counter)} descriptions missing."
                )
            elif description_missing_counter > 0:
                data_summary_d_fields["status"] = STATUS_CODE["WARNING"]
                data_summary_d_fields["message"] = MESSAGE_CODE["FREE_MESSAGE"](
                    f"{len(d.get(key))} fields: "
                    f"{len(description_missing_counter)} descriptions missing."
                )

        return data_summary_d_fields
