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
From the SC2 data, .xml files can be srced. Use the Dockerfile for this step:

```sh
docker build -t stormex-image ./src

docker run -v "path/to/starcraft/StarCraft II:/data/sc2data:ro" -v ./src/xml:/data/output stormex-image /data/sc2data -s .xml -x -o /data/output
```

Then merge relevant .xml files using order
```
liberty.sc2mod -> libertymulti.sc2mod -> balancemulti.sc2mod -> voidmulti.sc2mod
```
Run
```sh
uv run src/merge_xml.py --all
```

Finally we can convert the data from .xml to .json with
```sh
uv run src/convert_xml_to_json.py
```

From here we can generate the techtree
```sh
uv run src/generate_techtree.py
```

All in one:
```sh
uv run src/merge_xml.py --all && uv run src/convert_xml_to_json.py && uv run src/generate_techtree.py 
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
