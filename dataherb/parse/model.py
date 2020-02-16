import os
import logging
import yaml

logging.basicConfig()
logger = logging.getLogger("dataherb.parse.model")


class MetaData(object):
    def __init__(self):
        self.template = {
            "name": "",
            "description": "",
            "contributors": [
                {
                    "name": "",
                    "github": ""
                }
            ],
            "data": [
                {
                    "name": "",
                    "path": "",
                    "format": "",
                    "size": "",
                    "updated_at": "",
                    "fields": [
                        {
                            "name": "",
                            "description": ""
                        },
                        {
                            "name": "",
                            "description": ""
                        }
                    ]
                }
            ],
            "references": [
                {
                    "name": "",
                    "link": ""
                }
            ]
        }

    def create(self):

        # create .dataherb folder
        dataherb_folder = '.dataherb'
        try:
            os.mkdir(dataherb_folder)
            logger.info("Created ", dataherb_folder)
        except FileExistsError:
            logger.info(dataherb_folder,  " already exists!")

        metadata_file = 'metadata.yml'

        with open(os.path.join(dataherb_folder, metadata_file), 'w') as fp:
            documents = yaml.dump(self.template, fp)
