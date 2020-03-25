<h1 align="center">
  <br>
  <a href="https://dataherb.github.io"><img src="https://raw.githubusercontent.com/DataHerb/dataherb.github.io/master/assets/favicon/ms-icon-310x310.png" alt="Markdownify" width="200"></a>
  <br>
  The Python Package for DataHerb
  <br>
</h1>

<h4 align="center">A <a href="https://dataherb.github.io" target="_blank">DataHerb</a> Core Service to Create and Load Datasets.</h4>

<p align="center">

</p>



## Install

```
pip install dataherb
```

## The DataHerb Command-Line Tool

> Requires Python 3

The DataHerb cli provides tools to create dataset metadata, validate metadata, search dataset in flora, and download dataset.

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

We provide a template for dataset creation.

> Before creating a dataset, it is recommended that the user reads [the intro](#Understanding-DataHerb).

Use the following command line tool to create the metadata template.
```bash
dataherb create
```


## Use DataHerb in Your Code

### Load Data into DataFrame

```
# Load the package
from dataherb.flora import Flora

# Initialize Flora service
# The Flora service holds all the dataset metadata
dataherb = Flora()

# Search datasets with keyword(s)
geo_datasets = dataherb.search("geo")
print(geo_datasets)

# Get a specific file from a dataset and load as DataFrame
tz_df = dataherb.herb(
    "geonames_timezone"
).leaves.get(
    "dataset/geonames_timezone.csv"
).data
print(tz_df)

```


## The DataHerb Project


### What is DataHerb

DataHerb is an open data initiative to make the access of open datasets easier.

- A **DataHerb** or **Herb** is a dataset. A dataset comes with the data files, and the metadata of the data files.
- A **DataHerb Leaf** or **Leaf** is a data file in the DataHerb.
- A **Flora** is the combination of all the DataHerbs.

In many data projects, finding the right datasets to enhance your data is one of the most time consuming part. DataHerb adds flavor to your data project.

### What is DataHerb Flora

We desigined the following workflow to share and index datasets.

![DataHerb Workflow](https://raw.githubusercontent.com/DataHerb/dataherb.github.io/master/assets/images/dataherb-components.png)

This repository is being used for listing of datasets (Listings in DataHerb flora repository).

### How to Add Your Dataset

> [A Complete **Tutorals**](https://dataherb.github.io/add/)

Simply create a `yml` file in the `flora` folder to link to your dataset repository. Your dataset repository should have a `.dataherb` folder and a `metadata.yml` file in it.

The indexing part will be done by [GitHub Actions](https://github.com/DataHerb/dataherb-flora/actions).


## Development

1. Create a conda environment.
2. Install requirements: `pip install -r requirements.txt`

## Documentation

The documentation for this package is located at `docs`.

`HISTORY.rst` is used to list changes of the package.
