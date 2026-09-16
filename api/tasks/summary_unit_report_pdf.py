import tempfile

from analysis.lib.pdf.map import render_maps
from analysis.lib.pdf.report import create_report
from analysis.lib.stats.summary_units import get_summary_unit_results
from api.errors import DataError
from api.lib.progress import set_progress
from api.logger import log
from api.settings import TEMP_DIR


async def create_summary_unit_pdf_report(ctx, unit_type, unit_id):
    """Generate Midwest Blueprint Report for a HUC12

    Parameters
    ----------
    ctx : job context
    unit_type : str
        "huc12" (other types not currently supported)
    unit_id : str
    """

    errors = []
    await set_progress(ctx["redis"], ctx["job_id"], 0, "Calculating results")

    results = get_summary_unit_results(unit_type, unit_id)
    if results is None:
        raise DataError("Unit id is not valid (not an existing subwatershed or marine hex grid ID)")

    name = results["name"]

    await set_progress(ctx["redis"], ctx["job_id"], 50, "Creating maps (this might take a while)")

    # compile indicator IDs across all indicator groups
    indicators = []
    for group in results.get("indicator_groups", []):
        indicators.extend([i["id"] for i in group["indicators"]])

    maps, scale, map_errors = await render_maps(
        results["bounds"],
        summary_unit_id=unit_id,
        indicators=indicators,
        protected_areas="protected_areas" in results,
        urban="urban" in results,
    )

    if map_errors:
        log.error(f"Map rendering errors: {map_errors}")
        if "basemap" in map_errors:
            errors.append("Error creating basemap for all maps")

        if "aoi" in map_errors:
            errors.append("Error rendering area of interest on maps")

        if set(map_errors.keys()).difference(["basemap", "aoi"]):
            errors.append("Error creating one or more maps")

    await set_progress(
        ctx["redis"],
        ctx["job_id"],
        75,
        "Creating PDF (this might take a while)",
        errors=errors,
    )

    results["scale"] = scale

    pdf = create_report(maps=maps, results=results, name=results["name"], area_type=unit_type)

    await set_progress(ctx["redis"], ctx["job_id"], 95, "Nearly done", errors=errors)

    fp, local_filename = tempfile.mkstemp(suffix=".pdf", dir=TEMP_DIR)
    with open(fp, "wb") as out:
        out.write(pdf)

    await set_progress(ctx["redis"], ctx["job_id"], 100, "All done!", errors=errors)

    log.debug(f"Created PDF at: {local_filename}")

    download_filename = f"Midwest Blueprint Summary Report - {name}.pdf"

    return {
        "local_filename": local_filename,
        "download_filename": download_filename,
        "payload": f"/jobs/{ctx['job_id']}/pdf",
    }, errors
