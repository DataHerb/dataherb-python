# DataHerb Changelog

## Unreleased

Added:

- `dataherb catalog build | validate | lint | serve`: build a static DataHerb Explorer catalog site from `dataherb.config.yml` (git, S3, HTTP and local sources, S3 discovery, metadata quality scores).
- `dataherb status emit | check`: write and check job status files (`dataherb.status/v1`).
- DataHerb v2 metadata (owner, tags, license, classification, update frequency, status job, related datasets) with JSON Schemas in `dataherb/catalog/schemas`.
- Optional extras: `dataherb[s3]` (boto3), `dataherb[infer]` (duckdb).

Changed:

- `dataherb create [PATH]` infers resources and columns from csv, tsv, parquet and json files, asks for the v2 fields, supports `--no-input` and `--format yaml`, and only adds to the local flora when dataherb is configured.
- `dataherb validate [PATH]` checks metadata against the v2 schema, checks that listed files exist and prints a quality score (it was a stub before).
- `dataherb upload` uses the current directory (it used the package's install folder).
- "Loading Service" goes to stderr so command output can be piped.

## 0.1.4 - 2021-08-07

Added:

- Better search result formatting in terminal
- Show config using `dataherb configure --show`

Changed:

- Better config management

## 0.1.2 - 2021-08-06

Added `dataherb configure` to configure the command line too.
