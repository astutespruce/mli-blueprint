import re
from typing import Annotated
from urllib.parse import parse_qs, urlparse

import numpy as np
import typer

from analysis.constants import FILTER_DATASETS
from analysis.lib.filter.geotiff import FilterMode, save_to_geotiff

# create index by integer ID to match frontend
FILTER_DATASETS_INDEX = {i: k for i, k in enumerate(FILTER_DATASETS.keys())}


app = typer.Typer(help="Apply filters to Blueprint and save to GeoTIFF")


@app.command()
def apply_filters(
    url: Annotated[str, typer.Argument(help="URL saved in filter PDF for reopening filter state (see end of report)")],
    outfilename: Annotated[str, typer.Argument(help="Output GeoTIFF filename")],
):
    params = parse_qs(urlparse(url).query)
    filter_mode = params["filterMode"][0]
    if filter_mode not in FilterMode:
        raise typer.Exit(f"Invalid filter mode: {filter_mode}")

    filter_keys = [k for k in params if re.search(r"\d+", k)]
    invalid_keys = [k for k in filter_keys if int(k) not in FILTER_DATASETS_INDEX]
    if invalid_keys:
        raise typer.Exit(f"Invalid filter dataset indexes: {','.join(invalid_keys)}")

    filters = {
        FILTER_DATASETS_INDEX[int(index)]: np.array([int(v) for v in params[index][0].split(".")], dtype="uint8")
        for index in filter_keys
    }

    print(f"Applying the following filters to the Blueprint using {filter_mode} logic:")
    for id, values in filters.items():
        info = FILTER_DATASETS[id]
        print(f"  {info['label']}")
        values = set(values)
        value_labels = [v["label"] for v in info["values"] if v["value"] in values]
        for value in value_labels:
            print(f"  [x] {value}")

        print()

    save_to_geotiff(filter_mode, filters, outfilename)
