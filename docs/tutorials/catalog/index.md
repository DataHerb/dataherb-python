# Build a Catalog Website

`dataherb catalog` builds a static catalog and explorer website
([DataHerb Explorer](https://github.com/DataHerb/dataherb-explorer)) from a
`dataherb.config.yml` file and a folder of catalog entries. Datasets can live
in git repositories, S3 buckets, web servers or the catalog repository itself.

Fork DataHerb Explorer, edit its `dataherb.config.yml`, then:

```bash
pip install "dataherb[s3]"
dataherb catalog validate      # check the config and catalog entries
dataherb catalog lint          # metadata quality score per dataset
dataherb catalog build         # write the site to dist/
dataherb catalog serve         # preview at http://127.0.0.1:8000
```

`dataherb catalog lint --min-score 60` fails when any dataset scores lower,
which is useful in CI.

## Describe a dataset

In the folder that holds the data files:

```bash
pip install "dataherb[infer]"  # optional: duckdb for exact types of csv, parquet and json
dataherb create .              # asks a few questions
dataherb create . --no-input --format yaml --id orders   # infer only
dataherb validate .            # schema check, missing files, quality score
```

The metadata format (DataHerb v2) adds owner, tags, license,
classification, update frequency, related datasets and a status job to the
v1 `dataherb.json` format; v1 files remain valid.
