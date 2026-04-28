import asyncio
import json
import os
from base64 import b64decode, b64encode
from pathlib import Path
from time import time

from pyogrio.geopandas import read_dataframe
import shapely
from progress.bar import Bar

from analysis.constants import DATA_CRS, GEO_CRS, M2_ACRES
from analysis.lib.geometry import dissolve
from api.report import create_report
from api.report.map import render_maps
from api.stats.custom_area import get_custom_area_results
from api.stats.summary_units import get_summary_unit_results

# if True, cache maps if not previously created, then reuse
CACHE_MAPS = False


def write_cache(maps, scale, path):
    if not path.exists():
        os.makedirs(path)

    for name, data in maps.items():
        if data is not None:
            with open(path / f"{name.replace(':', '__')}.png", "wb") as out:
                out.write(b64decode(data))

    with open(path / "scale.json", "w") as out:
        out.write(json.dumps(scale))


def read_cache(path):
    if not path.exists():
        # cache miss
        return None, None

    maps = {}
    for filename in path.glob("*.png"):
        name = filename.stem.replace("__", ":")
        maps[name] = b64encode(open(filename, "rb").read()).decode("utf-8")

    scale = json.loads(open(path / "scale.json").read())

    print("CACHE: loaded maps from cache")

    return maps, scale


### Create reports for an AOI
aois = [
    {"name": "", "path": "test_wi_rect"}
    # {"name": "", "path": "in_lake_michigan"},
    # {"name": "", "path": "overlap_ne_mli_boundary"},
]

for aoi in aois:
    name = aoi["name"]
    path = aoi["path"]
    print(f"Creating report for {name}...")

    filename = Path("examples") / f"{path}.shp"

    start = time()
    df = read_dataframe(filename, columns=[], force_2d=True).to_crs(DATA_CRS)
    df["geometry"] = shapely.make_valid(df.geometry.values)
    df["group"] = 1
    df = dissolve(df.explode(ignore_index=True), by="group")

    extent_area = shapely.area(shapely.box(*df.total_bounds)) * M2_ACRES
    print(
        f"Area of extent: {extent_area:,.0f} acres",
    )
    print(f"Area of geometry: {df.area.sum() * M2_ACRES:,.0f} acres")

    ### calculate results, data must be in DATA_CRS
    bar = Bar("Summarizing rasters", max=100, suffix="%(percent)d%%")

    async def progress_callback(percent):
        bar.next(percent)

    print("Calculating results...")
    task = get_custom_area_results(df, progress_callback=progress_callback)
    results = asyncio.run(task)

    bar.finish()

    if results is None:
        print(f"AOI: {path} does not overlap Blueprint")
        continue

    out_dir = Path("/tmp/aoi") / path
    if not out_dir.exists():
        os.makedirs(out_dir)

    cache_dir = out_dir / "maps"

    maps = None
    scale = None
    if CACHE_MAPS:
        maps, scale = read_cache(cache_dir)

    if not maps:
        print("Rendering maps...")

        # compile indicator IDs across all indicator groups
        indicators = []
        for group in results.get("indicator_groups", []):
            indicators.extend([i["id"] for i in group["indicators"]])

        geo_df = df.to_crs(GEO_CRS)
        task = render_maps(
            geo_df.total_bounds,
            geometry=geo_df.geometry.values[0],
            indicators=indicators,
            protected_areas="protected_areas" in results,
            urban="urban" in results,
            add_mask=results["acres"] >= 1e9,
        )

        maps, scale, errors = asyncio.run(task)

        if errors:
            print("Errors", errors)

        if CACHE_MAPS:
            write_cache(maps, scale, cache_dir)

    results["scale"] = scale

    pdf = create_report(maps=maps, results=results, name=name)

    with open(out_dir / f"{path}_report.pdf", "wb") as out:
        out.write(pdf)

    print("Elapsed {:.2f}s".format(time() - start))

############################################################

## Create reports for summary units
ids = {
    "huc12": [
        # "070600030303",
        # "041900000200"  # Lake Michigan islands
    ],
}


for unit_type in ids:
    for unit_id in ids[unit_type]:
        print(f"Creating report for for {unit_id}...")

        out_dir = Path(f"/tmp/{unit_id}")
        cache_dir = out_dir / "maps"

        if not out_dir.exists():
            os.makedirs(out_dir)

        # Fetch results
        results = get_summary_unit_results(unit_type, unit_id)

        # compile indicator IDs across all inputs
        indicators = []
        for group in results.get("indicator_groups", []):
            indicators.extend([i["id"] for i in group["indicators"]])

        maps = None
        if CACHE_MAPS:
            maps, scale = read_cache(cache_dir)

        if not maps:
            print("Rendering maps...")
            task = render_maps(
                results["bounds"],
                summary_unit_id=unit_id,
                indicators=indicators,
                protected_areas="protected_areas" in results,
                urban="urban" in results,
            )
            maps, scale, errors = asyncio.run(task)

            if errors:
                print("Errors", errors)

            if CACHE_MAPS:
                write_cache(maps, scale, cache_dir)

        results["scale"] = scale

        pdf = create_report(maps=maps, results=results, name=results["name"], area_type=unit_type)

        with open(out_dir / f"{unit_id}_report.pdf", "wb") as out:
            out.write(pdf)
