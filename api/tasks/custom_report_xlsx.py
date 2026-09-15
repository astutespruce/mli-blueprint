from pathlib import Path

import geopandas as gp
from pyogrio import read_info

from analysis.constants import DATA_CRS
from analysis.lib.geometry import dissolve
from analysis.lib.stats.analysis_units import get_analysis_unit_results
from analysis.lib.stats.prescreen import get_available_datasets
from analysis.lib.xlsx.report import create_report
from api.errors import DataError
from api.lib.geo import extract_dataset
from api.lib.progress import set_progress
from api.logger import log
from api.settings import TEMP_DIR

VALID_ID_FIELD_DTYPES = {"object", "int8", "uint8", "int16", "uint16", "int32", "uint32", "int64", "uint64"}


async def get_xlsx_report_inputs(ctx, zip_filename, dataset, layer, uuid):
    zip_filename = Path(zip_filename)

    await set_progress(ctx["redis"], ctx["job_id"], 0, "Extracting analysis areas")

    path = f"/vsizip/{zip_filename}/{dataset}"
    info = read_info(path, layer=layer)

    # prescreen columns to read to exclude floating point, dates
    id_fields = [field for field, dtype in zip(info["fields"], info["dtypes"]) if dtype in VALID_ID_FIELD_DTYPES]

    df = extract_dataset(path, layer=layer, columns=id_fields).to_crs(DATA_CRS)

    # drop any fields that are completely null
    fields = {col: len(df[col].unique()) for col in id_fields if not df[col].isnull().all()}

    # Save as feather file for subsequent steps
    df[["geometry"] + list(fields.keys())].to_feather(zip_filename.with_suffix(".feather"))

    ### prescreen datasets available
    await set_progress(ctx["redis"], ctx["job_id"], 50, "Checking available datasets")
    datasets = get_available_datasets(df)

    if len(datasets) == 0:
        raise DataError(
            "area of interest does not overlap Southeast Blueprint or area of interest did not overlap with the center of at least one 30m pixel in the Southeast Blueprint"
        )

    await set_progress(ctx["redis"], ctx["job_id"], 100, "Done checking available datasets")

    return {
        "payload": {
            # pass along uuid from task context
            "uuid": uuid,
            "count": info["features"],
            "fields": fields,
            "datasets": datasets,
        }
    }, []


async def create_custom_xlsx_report(
    ctx, uuid: str, datasets: str, field: str | None = None, name: str | None = None
) -> tuple[dict, list]:
    """Create XLSX report for analysis areas specified by uuid for all listed
    datasets, aggregated by field if provided.

    Parameters
    ----------
    ctx : arq context
    uuid : str
        stem of temporary filename for feather file of input data
    datasets : str
        comma-delimited list of datasets to analyze
    field : str or None, optional (default: None)
        field to aggregate results by
    name : str or None, optional (default: None)
        name of area, to include in report

    Returns
    -------
    tuple[dict, list]
        [{"payload": <filename>}, errors]
    """

    datasets = set(datasets.split(","))

    await set_progress(ctx["redis"], ctx["job_id"], 0, "Reading dataset")

    filename = TEMP_DIR / f"{uuid}.feather"

    # double-check that it exists; this should not occur here
    # because we check for it before submitting job
    if not filename.exists():
        log.error(f"Dataset does not exist for uuid: {uuid}")
        raise ValueError("Dataset does not exist")

    columns = [field] if field else []
    df = gp.read_feather(filename, columns=["geometry"] + columns)

    if not field:
        field = "__analysis_unit"
        df[field] = "all areas"

    if len(df) > 1:
        await set_progress(ctx["redis"], ctx["job_id"], 5, "Aggregating boundaries")

        try:
            df = dissolve(df, by=field).set_index(field)

        except Exception as ex:
            log.error(f"Failed to dissolve dataframe: {filename} on field: {field}")
            log.error(ex)
            raise DataError("Could not aggregate boundaries for analysis")

    else:
        df = df.set_index(field)

    await set_progress(ctx["redis"], ctx["job_id"], 10, "Calculating statistics (may take a while)")

    async def progress_callback(percent):
        await set_progress(
            ctx["redis"],
            ctx["job_id"],
            # ranges 10-75%
            int(round(10 + (percent / 100) * 65)),
            "Calculating statistics (may take a while)",
        )

    results = await get_analysis_unit_results(df, datasets, progress_callback=progress_callback)
    if results is None:
        raise DataError("Dataset does not overlap Southeast states")

    await set_progress(ctx["redis"], ctx["job_id"], 75, "Creating XLSX file")
    xlsx = create_report(results, datasets, name)

    await set_progress(ctx["redis"], ctx["job_id"], 95, "Nearly done")

    local_filename = str(TEMP_DIR / f"{uuid}.xlsx")

    with open(local_filename, "wb") as out:
        out.write(xlsx)

    log.debug(f"Created XLSX at: {local_filename}")

    await set_progress(ctx["redis"], ctx["job_id"], 100, "All done!")

    download_filename = (
        f"Southeast Blueprint Summary Report - {name}.xlsx" if name else "Southeast Blueprint Summary Report.xlsx"
    )

    return {
        "local_filename": local_filename,
        "download_filename": download_filename,
        "payload": f"/jobs/{ctx['job_id']}/xlsx",
    }, []
