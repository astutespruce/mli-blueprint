import asyncio
from pathlib import Path
from time import time

from progress.bar import Bar
from pyogrio import read_dataframe

from analysis.constants import DATA_CRS, GEO_CRS
from api.report import create_report
from api.report.map import render_maps
from api.stats.custom_area import get_custom_area_results


bnd_dir = Path("data/boundaries")
out_dir = Path("/tmp/mli")
out_dir.mkdir(exist_ok=True)


states = read_dataframe(bnd_dir / "states_for_reports.fgb", use_arrow=True).to_crs(DATA_CRS).sort_values(by="state")

for state in states.state.values:
    print(f"Creating report for {state}")

    start = time()

    df = states.loc[states.state == state]

    bar = Bar("Summarizing rasters", max=100, suffix="%(percent)d%%")

    async def progress_callback(percent):
        bar.next(percent)

    print("Calculating results...")
    task = get_custom_area_results(df, progress_callback=progress_callback)
    results = asyncio.run(task)

    bar.finish()

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
        add_mask=True,
    )

    maps, scale, errors = asyncio.run(task)

    if errors:
        print("Errors", errors)

    results["scale"] = scale

    pdf = create_report(maps=maps, results=results, name=state)

    with open(out_dir / f"{state.replace(' ', '_')}_Blueprint2026_report.pdf", "wb") as out:
        out.write(pdf)

    print("Elapsed {:.2f}s".format(time() - start))
