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

# src data
From the SC2 data, .xml files can be extracted. Use the Dockerfile for this step:

```sh
docker build -t stormex-image ./src

docker run -v "path/to/starcraft/StarCraft II:/data/sc2data:ro" -v ./src/xml:/data/output stormex-image /data/sc2data -s .xml -x -o /data/output
```

```sh
# Creates src/extracted/stableid.json
docker run -v "path/to/starcraft/StarCraft II:/data/sc2data:ro" -v ./src/extracted:/data/output/mods/core.sc2mod/base.sc2data/GameData stormex-image /data/sc2data -s stableid.json -x -o /data/output
```

Convert the data from .xml to .json with
```sh
# Creates .../*Data.json
uv run src/xml_to_json.py
```

Then merge relevant .json files using order
```
liberty.sc2mod -> libertymulti.sc2mod -> swarm.sc2mod -> swarmmulti.sc2mod -> void.sc2mod -> voidmulti.sc2mod
```
Run
```sh
# Creates src/merged/*Data.xml
uv run src/merge_json.py
```

From here we can generate the techtree (all units, all abilities)
```sh
# Creates src/json/techtree.json
uv run src/generate_techtree.py
```

A smaller version of the techtree (with only real units and hardcoded suppressions) can be generated with
```sh
# Creates src/computed/data.json
uv run src/reconstruct_data.py
``` 

All in one:
```sh
uv run src/xml_to_json.py && uv run src/merge_json.py && uv run src/generate_techtree.py && uv run src/reconstruct_data.py
```

Resulting files should be:
```sh
src/
├── Dockerfile
├── merge_xml.py
├── convert_xml_to_json.py
├── xml/ # srced from SC2
│   ├── campaigns/
│   └── mods/ # Load order
│       ├── liberty.sc2mod/
│       ├── libertymulti.sc2mod/
│       ├── balancemulti.sc2mod/
│       └── voidmulti.sc2mod/
├── merged/ # Merged XML
└── json/ # Final JSON output
```

# Missing data? Invalid data? Other issues?

Please [open a new issue in GitHub](https://github.com/BurnySc2/sc2-techtree/issues/new).

Pull requests to fix things or for extensions are welcome as well,
although I suggest asking me first by opening an issue or otherwise.
The data model changes are usually quite hard to get right, and the
data collection script itself is quite complicated and full of edge
cases.
