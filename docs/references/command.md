## Command Line Tool



!!! warning
    Requires Python 3.

The DataHerb cli tool provides some utilities to create dataset metadata, validate metadata, search dataset in flora, upload dataset to remote, and download dataset.


### Create Dataset

Suppose you have some csv files in a folder called `my_csv_data`.

Get into the folder

```bash
cd my_csv_data
```

Run

```bash
dataherb create
```

and answer a few questions.

Behind the scenes, the answers to these questions will be combined with the inferred schema of the dataset by [datapackage](https://github.com/frictionlessdata/datapackage-py).


### Search and Download

Search by keyword

```
dataherb search covid19
# Shows the minimal metadata
```

Search by dataherb id

```
dataherb search -i covid19_eu_data
# Shows the full metadata
```

Download dataset by dataherb id

```
dataherb download covid19_eu_data
# Downloads this dataset: http://dataherb.io/flora/covid19_eu_data
```


### Create Dataset Using Command Line Tool

Dataherb provides a template for dataset creation.

Within a dataset folder where the data files are located, use the following command line tool to create the metadata template.

```bash
dataherb create
```

!!! warning
    It is recommended that one go though the generated `dataherb.json` file in the folder and make sure things like names and descriptions are correct. Sometimes human simply creates typos.


### Upload dataset to remote

Within the dataset folder, run

```bash
dataherb upload
```



### UI for all the datasets in a flora


```bash
dataherb serve
```

A website will be running and we can browse all the datasets. Dataset search is also included.

!!! note
    The website is built with mkdocs. It is also very easy to deploy the generate website to any server that supports static html.
