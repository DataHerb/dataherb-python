site_config = """site_name: My DataHerb

docs_dir: herbs

theme:
  name: "material"
  include_search_page: false
  search_index_only: true

  language: en
  features:
    - navigation.sections
    - navigation.instant
  palette:
    - scheme: default
      primary: indigo
      accent: indigo
      toggle:
        icon: material/toggle-switch-off-outline
        name: Switch to dark mode
    - scheme: slate
      primary: red
      accent: red
      toggle:
        icon: material/toggle-switch
        name: Switch to light mode




markdown_extensions:
  - meta
  - admonition

plugins:
  - search
  - macros
"""


index_template = """---
title: Home
---

This is the landing page of DataHerb.
"""
