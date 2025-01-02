# StarCraft II tech tree and dependencies

All SC2 structures, units, abilities, researches and dependencies between these, in machine readable JSON format.

This repository contains Python scripts for data generation.

# Development

- Install StarCraft II (and for linux set environment variables) [similar to the instructions here](https://github.com/BurnySc2/python-sc2#installation)
- Install python3.9 or newer
- Install `uv` via `pip install uv`

The Python code to generate new data is the directory `generate`.

You can run

```py
uv run --env-file=.env python run.py
```

to generate a new `/data/data.json`.

# Missing data? Invalid data? Other issues?

Please [open a new issue in GitHub](https://github.com/BurnySc2/sc2-techtree/issues/new).

Pull requests to fix things or for extensions are welcome as well,
although I suggest asking me first by opening an issue or otherwise.
The data model changes are usually quite hard to get right, and the
data collection script itself is quite complicated and full of edge
cases.
