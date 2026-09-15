import asyncio
from typing import Annotated
from zipfile import ZipFile

import typer
from pyogrio import read_dataframe, read_info

from analysis.constants import DATA_CRS, GEO_CRS, REPORT_DATASETS
from analysis.lib.geometry import dissolve
from analysis.lib.pdf.map import render_maps
from analysis.lib.pdf.report import create_report as create_pdf_report
from analysis.lib.stats.analysis_units import get_analysis_unit_results
from analysis.lib.stats.aoi import get_aoi_results
from analysis.lib.stats.prescreen import get_available_datasets
from analysis.lib.xlsx.report import create_report as create_xlsx_report
from api.lib.geo import extract_dataset, get_dataset
from api.tasks.custom_report_xlsx import VALID_ID_FIELD_DTYPES

app = typer.Typer(help="Create a Blueprint report")


async def _create_pdf_report(filename: str, outfilename: str, area_name: str | None = None):
    if filename.endswith(".shp") or filename.endswith(".gdb"):
        df = read_dataframe(filename, columns=[], use_arrow=True).to_crs(DATA_CRS)
    elif filename.endswith(".zip"):
        with ZipFile(filename) as zipfile:
            dataset, layer = get_dataset(zipfile)
            df = read_dataframe(f"/vsizip/{filename}/{dataset}", layer=layer, columns=[], use_arrow=True).to_crs(
                DATA_CRS
            )
    else:
        raise typer.Exit(f"ERROR: unsupported file type: {filename}")

    with typer.progressbar(length=100, label="Creating report") as progress:
        df = dissolve(df)
        geo_df = df.to_crs(GEO_CRS)
        progress.update(10)

        async def progress_callback(percent):
            progress.update(int(round(10 + (percent / 100) * 50)))

        results = await get_aoi_results(df, progress_callback=progress_callback)

        indicators = []
        for group in results.get("indicator_groups", []):
            indicators.extend([i["id"] for i in group["indicators"]])

        maps, scale, map_errors = await render_maps(
            geo_df.total_bounds,
            geometry=geo_df.geometry.values[0],
            indicators=indicators,
            protected_areas="protected_areas" in results,
            urban="urban" in results,
            add_mask=results["acres"] >= 1e9,
        )
        progress.update(80)

        assert len(map_errors) == 0

        results["scale"] = scale

        pdf = create_pdf_report(maps=maps, results=results, name=area_name)
        progress.update(95)

        with open(outfilename, "wb") as out:
            _ = out.write(pdf)

        progress.update(100)


async def _create_xlsx_report(
    filename: str, outfilename: str, area_name: str | None = None, field: str | None = None, datasets: str | None = None
):
    columns = [field] if field else []
    datasets = {d.strip() for d in datasets.split(",")} if datasets else set()
    invalid = {d for d in datasets if d not in REPORT_DATASETS}
    if invalid:
        raise typer.Exit(f"ERROR: invalid datasets: {', '.join(invalid)}")

    if filename.endswith(".shp") or filename.endswith(".gdb"):
        path = filename
        layer = None
    elif filename.endswith(".zip"):
        with ZipFile(filename) as zipfile:
            dataset, layer = get_dataset(zipfile)
            path = f"/vsizip/{filename}/{dataset}"

    else:
        raise typer.Exit(f"ERROR: unsupported file type: {filename}")

    available_fields = set(read_info(path, layer=layer)["fields"])
    if field not in available_fields:
        raise typer.Exit(f"ERROR: field '{field}' is not present in dataset")

    df = read_dataframe(path, layer=layer, columns=columns, use_arrow=True).to_crs(DATA_CRS)

    with typer.progressbar(length=100, label="Creating report") as progress:
        if len(df) > 1:
            df = dissolve(df, by=field)

        if not field:
            field = "__analysis_unit"
            df[field] = "all areas"

        df = df.set_index(field)

        progress.update(10)

        if not datasets:
            datasets = get_available_datasets(df)

        progress.update(20)

        async def progress_callback(percent):
            progress.update(int(round(20 + (percent / 100) * 50)))

        results = await get_analysis_unit_results(df, datasets, progress_callback=progress_callback)

        xlsx = create_xlsx_report(results, datasets, name=area_name)
        progress.update(95)

        with open(outfilename, "wb") as out:
            _ = out.write(xlsx)

        progress.update(100)


@app.command(help="Create a PDF report")
def pdf(
    filename: Annotated[str, typer.Argument(help="shapefile or FGDB filename")],
    outfilename: Annotated[str, typer.Argument(help="output PDF filename")],
    area_name: Annotated[str | None, typer.Option(help="name of the area of interest (included in report)")] = None,
):
    asyncio.run(_create_pdf_report(filename, outfilename, area_name))


@app.command(help="Create an XLSX report")
def xlsx(
    filename: Annotated[str, typer.Argument(help="shapefile or FGDB filename")],
    outfilename: Annotated[str, typer.Argument(help="output XLSX filename")],
    area_name: Annotated[str | None, typer.Option(help="name of the area of interest (included in report)")] = None,
    field: Annotated[str | None, typer.Option(help="field (column) name to use for aggregating statistics")] = None,
    datasets: Annotated[
        str | None,
        typer.Option(
            help="comma-delimited list of datasets to include in report; by default all overlapping datasets are included"
        ),
    ] = None,
):
    asyncio.run(_create_xlsx_report(filename, outfilename, area_name, field, datasets))


@app.command(help="Get info about a shapefile or FGDB")
def info(filename: Annotated[str, typer.Argument(help="shapefile or FGDB filename")]):
    if filename.endswith(".shp") or filename.endswith(".gdb"):
        path = filename
        dataset = filename
        layer = None
    elif filename.endswith(".zip"):
        with ZipFile(filename) as zipfile:
            dataset, layer = get_dataset(zipfile)
            path = f"/vsizip/{filename}/{dataset}"
    else:
        raise typer.Exit(f"ERROR: unsupported file type: {filename}")

    info = read_info(path, layer=layer)

    # prescreen columns to read to exclude floating point, dates
    id_fields = [field for field, dtype in zip(info["fields"], info["dtypes"]) if dtype in VALID_ID_FIELD_DTYPES]

    df = extract_dataset(path, layer=layer, columns=id_fields).to_crs(DATA_CRS)

    # drop any fields that are completely null
    fields = {col: len(df[col].unique()) for col in id_fields if not df[col].isnull().all()}

    print(f"{dataset}" + f" ({layer})" if layer is not None else "")
    print(f"features: {info['features']}")
    print("fields:")
    for field, count in fields.items():
        print(f"\t{field}: {count} unique values")
