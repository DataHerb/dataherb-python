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

!!! warning "config file already exists"
    If a config file (`~/.dataherb/config.json`) is already created, a warning will be shown:

    ```bash
    Config file (~/.dataherb/config.json) already exists
    ```

    You could overwrite it or leave it be.



### Manually Create Configuration

Once the `dataherb configure` command is run, a `config.json` file will be created inside the folder `~/.dataherb`.

```json
{
    "workdir": "~/dataherb",
    "default": {
        "flora": "flora"
    }
}
```

| key  |  example | description |
|---|---|---|
| `workdir`  |  `~/dataherb` | The work directory for dataherb. |
| `default.flora`  | `flora` |  The name of the flora to be used by default. For example, the value `flora` means we will use the `flora.json` database in the folder `(workdir setting in the above row)/flora/flora.json`. |


!!! note "More about `workdir`"
    By default, two folders will be created inside it: `~/dataherb/flora` (default storage for all flora) and `~/dataherb/serve` (the cache folder for the website of all datasets when we run `dataherb serve`)

!!! note "More about `default.flora`"
    If `workdir` is set to `~/dataherb`, then the database will be `~/dataherb/flora/flora.json`. If the value of `default.flora` is set to `abc`, then the database will be `~/dataherb/flora/abc.json`.