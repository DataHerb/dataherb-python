## Configuration


Configuring `dataherb` is easy. It can be done using the built-in `dataherb configure` comamnd or manually.


### Using Command Line Tool

Run the command

```bash
dataherb configure
```

and some questions will show up:

```bash
[?] Where should I put all the datasets and flora database? An empty folder is recommended.: ~/dataherb
[?] How would you name the default flora? Please keep the default value if this is not clear to you.: flora
```

The first question is setting the workdir.

!!! warning "Different ways of perserving the metadata"
    We have two different ways of perserving the flora meta data.

    1. Using a single file for all the datasets.
    2. Using a folder for each dataset.

    `dataherb` supports both. By default, we will use folders. For the above configuration, we will find the folder for all the flora metadata at `~/dataherb/flora/flora`.

    Note that `~/[workdir]/flora/` is the path where we put all the flora metadata. If the answer to the second question, aka name of the flora, is set to `flora2`, we will have all the flora metadata located at `~/[workdir]/flora/flora`2`.

    We can have multiple flora, for example, we can have two, `flora` and `flora2`

    ```bash
    flora
    ├── flora
    │   └── git-dataherb-python-demo-dataset
    │        └── dataherb.json
    └── flora2
        └── git-dataherb-python-demo-dataset-2
            └── dataherb.json
    ```

!!! warning "config file already exists"
    If a config file (`~/.dataherb/config.json`) is already created, a warning will be shown:

    ```bash
    Config file (~/.dataherb/config.json) already exists
    ```

    You could overwrite it or leave it be.


### Show Current Configuration

To inspect the current configuration, use the option `-s` (or `--show`).

```bash
dataherb configure -s
```

We will get something similar to the following.

```bash
The current config for dataherb is:
{
  "default": {
    "flora": "flora"
  },
  "workdir": "/Users/itsme/dataherb"
}
The above config is extracted from ~/.dataherb/config.json
```

### Locate the Configuration File

The option `-l` (or `--locate`) opens the folder that contains the configuration file `config.json`.

```bash
dataherb configure -l
```


### Manually Create Configuration

Once the `dataherb configure` command is run, a `config.json` file will be created inside the folder `~/.dataherb`.

```json
{
    "workdir": "~/dataherb",
    "default": {
        "flora": "flora",
        "aggregrated": false
    }
}
```

| key  |  example | description |
|---|---|---|
| `workdir`  |  `~/dataherb` | The work directory for dataherb. |
| `default.flora`  | `flora` |  The name of the flora to be used by default. For example, the value `flora` means we will use the `flora.json` database in the folder `(workdir setting in the above row)/flora/flora.json`. |
| `default.aggregrated`  | `false` |  Whether to use a single json file for all the flora metadata. It is highly recommended to set it to `false`. |


!!! note "More about `workdir`"
    By default, two folders will be created inside it: `~/dataherb/flora` (default storage for all flora) and `~/dataherb/serve` (the cache folder for the website of all datasets when we run `dataherb serve`)

!!! note "More about `default.flora`"
    If `workdir` is set to `~/dataherb`, then the database will be `~/dataherb/flora/flora`. If the value of `default.flora` is set to `abc`, then the database will be `~/dataherb/flora/abc`.
