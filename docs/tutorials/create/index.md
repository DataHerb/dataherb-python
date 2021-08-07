## Create New Dataset

!!! warning "The demo dataset"
    We will use the data files in [this repository](https://github.com/DataHerb/dataherb-python-demo-dataset) as a demo. Please [download the zip of this repo](https://github.com/emptymalei/dataherb-serve/archive/refs/heads/master.zip).



### Create


After downloading and unzipping [the demo dataset](https://github.com/emptymalei/dataherb-serve/archive/refs/heads/master.zip), `cd` into the folder. In my case, it is

```bash
cd ~/Downloads/dataherb-python-demo-dataset-main
```

Run the command

```bash
dataherb create
```

and a few questions will pop out.

```bash
Your current working directory is /Users/itsme/Downloads/dataherb-python-demo-dataset-main
A dataherb.json file will be created right here.
Are you sure this is the correct path? [y/N]: y
```

This makes sure that we are working in the correct folder. In this case, we type `y` to confirm.

#### Which Type of Remote

```bash
[?] Where is/will be the dataset synced to?: git
 > git
   s3
```

Dataherb supports two different types of sources, S3 and git. In this case, we choose `git` as we would like to sync the dataset to a GitHub repo.

#### Name of the Dataset

```bash
[?] How would you like to name the dataset?: Dataherb Demo Dataset
```

This will be the name of your dataset.

#### ID of the Dataset

```bash
[?] Please specify a unique id for the dataset: git-dataherb-python-demo-dataset
```

ID of the dataset has to be unique in your whole flora.

#### Description

```bash
[?] What is the dataset about? This will be the description of the dataset.: This is a demo dataset to test and show dataherb.
```

Describe the dataset here.

#### URI

```bash
[?] What is the dataset's URI? This will be the URI of the dataset.: https://github.com/DataHerb/dataherb-python-demo-dataset-created.git
```




### Result

Two things happened after this.

1. A file `dataherb.json` will be created in the current folder.
2. The metadata for this dataset has been added to the Flora.



!!! note "Content of the `dataherb.json` file"
    The content of the file should be the following.

    ```json
    {
        "source": "git",
        "name": "Dataherb Demo Dataset",
        "id": "git-dataherb-python-demo-dataset",
        "description": "This is a demo dataset to test and show dataherb.",
        "uri": "https://github.com/DataHerb/dataherb-python-demo-dataset-created.git",
        "metadata_uri": "https://raw.githubusercontent.com/DataHerb/dataherb-python-demo-dataset-created/main/dataherb.json",
        "datapackage": {
            "profile": "tabular-data-package",
            "resources": [
                {
                    "path": "dataset/indeed_job_listing.csv",
                    "profile": "tabular-data-resource",
                    "name": "indeed_job_listing",
                    "format": "csv",
                    "mediatype": "text/csv",
                    "encoding": "windows-1252",
                    "schema": {
                        "fields": [
                            {
                                "name": "title",
                                "type": "string",
                                "format": "default"
                            },
                            {
                                "name": "location",
                                "type": "string",
                                "format": "default"
                            },
                            {
                                "name": "company",
                                "type": "string",
                                "format": "default"
                            },
                            {
                                "name": "description",
                                "type": "string",
                                "format": "default"
                            },
                            {
                                "name": "salary",
                                "type": "string",
                                "format": "default"
                            },
                            {
                                "name": "url",
                                "type": "string",
                                "format": "default"
                            },
                            {
                                "name": "published_at",
                                "type": "string",
                                "format": "default"
                            },
                            {
                                "name": "id",
                                "type": "string",
                                "format": "default"
                            }
                        ],
                        "missingValues": [
                            ""
                        ]
                    }
                },
                {
                    "path": "dataset/stackoverflow_job_listing.csv",
                    "profile": "tabular-data-resource",
                    "name": "stackoverflow_job_listing",
                    "format": "csv",
                    "mediatype": "text/csv",
                    "encoding": "utf-8",
                    "schema": {
                        "fields": [
                            {
                                "name": "link",
                                "type": "string",
                                "format": "default"
                            },
                            {
                                "name": "category",
                                "type": "string",
                                "format": "default"
                            },
                            {
                                "name": "title",
                                "type": "string",
                                "format": "default"
                            },
                            {
                                "name": "description",
                                "type": "string",
                                "format": "default"
                            },
                            {
                                "name": "published_at",
                                "type": "string",
                                "format": "default"
                            },
                            {
                                "name": "location",
                                "type": "string",
                                "format": "default"
                            },
                            {
                                "name": "stackoverflow_id",
                                "type": "integer",
                                "format": "default"
                            },
                            {
                                "name": "author",
                                "type": "string",
                                "format": "default"
                            },
                            {
                                "name": "location_country",
                                "type": "string",
                                "format": "default"
                            },
                            {
                                "name": "location_city",
                                "type": "string",
                                "format": "default"
                            },
                            {
                                "name": "updated_at",
                                "type": "string",
                                "format": "default"
                            }
                        ],
                        "missingValues": [
                            ""
                        ]
                    }
                }
            ]
        }
    }
    ```



### Sync to Remote


!!! warning "WIP"
    Sync local dataset to remote is still a WIP.


After creating the dataset, run the command `dataherb upload`.

!!! warning "Using Experimental Feature"
    Use `dataherb upload --experimental True` to use experimental feature. For example, git repo will automatically add, commit ,and push.
