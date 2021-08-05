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

Documentation: [dataherb.github.io/dataherb-python](https://dataherb.github.io/dataherb-python)

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

Within a dataset folder where the data files are located, use the following command line tool to create the metadata template.

```bash
dataherb create
```

### Upload dataset to remote

Within the dataset folder, run

```bash
dataherb upload
```

### UI for all the datasets in a flora


```bash
dataherb serve
```


## Use DataHerb in Your Code

### Load Data into DataFrame

```
# Load the package
from dataherb.flora import Flora

# Initialize Flora service
# The Flora service holds all the dataset metadata
use_flora = "path/to/my/flora.json"
dataherb = Flora(flora=use_flora)

# Search datasets with keyword(s)
geo_datasets = dataherb.search("geo")
print(geo_datasets)

# Get a specific file from a dataset and load as DataFrame
tz_df = pd.read_csv(
  dataherb.herb(
      "geonames_timezone"
  ).get_resource(
      "dataset/geonames_timezone.csv"
  )
)
print(tz_df)
```


## The DataHerb Project


### What is DataHerb

DataHerb is an open-source data discovery and management tool.

- A **DataHerb** or **Herb** is a dataset. A dataset comes with the data files, and the metadata of the data files.
- A **Herb Resource** or **Resource** is a data file in the DataHerb.
- A **Flora** is the combination of all the DataHerbs.

In many data projects, finding the right datasets to enhance your data is one of the most time consuming part. DataHerb adds flavor to your data project. By creating metadata and manage the datasets systematically, locating an dataset is much easier.

Currently, dataherb supports sync dataset between local and S3/git. Each dataset can have its own remote location.

### What is DataHerb Flora

We desigined the following workflow to share and index open datasets.

![DataHerb Workflow](https://raw.githubusercontent.com/DataHerb/dataherb.github.io/master/assets/images/dataherb-components.png)

> The repo [dataherb-flora](https://github.com/DataHerb/dataherb-flora) is a demo flora that lists some datasets and demonstrated on the website [https://dataherb.github.io](https://dataherb.github.io). At this moment, the whole system is being renovated.

## Development

1. Create a conda environment.
2. Install requirements: `pip install -r requirements.txt`

## Documentation

The source of the documentation for this package is located at `docs`.


## References and Acknolwedgement

- `dataherb` uses `datapackage` in the core. `datapackage` is a python library for the [data-package standard](https://specs.frictionlessdata.io/data-package/). The core schema of the dataset is essentially the data-package standard.