## Tutorials

This is a series of tutorials to help you get started with `dataherb`.

### Herbs and Flora

The name Dataherb is a metaphor. Each data file is like a **Leaf** (or **Resource**) of a **Herb** (or **Dataset**). Many Herbs form a **Flora**.

| Dataherb Term | Meaning |
|-----|-----|
| Herb | A Dataset |
| Resource | A Data File |

!!! note "Leaf and Resource"
    Leaf is an alias of Resource.

### Managing the Flora

This python package ships a command line tool that can be used to manage the **Flora**.

The core of a flora is basically a json file that lists the metadata of herbs. The default flora can be configured using `dataherb configure`.

Using this configuration, we can simply store the json representing the flora and recreate the whole flora on other devices.

!!! note "Sync the Flora to GitHub"
    For example, we can version control the flora and push it to GitHub and pull it down on other devices. In this way, we can sync and restore the flora.


