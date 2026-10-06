from datetime import date

import pandas as pd
from openpyxl.styles import Color, Font

from analysis.constants import (
    BLUEPRINT,
    INDICATOR_GROUPS,
    INDICATORS,
    PROTECTED_AREAS,
    PROTECTED_AREAS_POLY,
    REPORT_DATASETS,
    URBAN_BY_DECADE,
)
from analysis.lib.xlsx.writer import write_excel


def add_data_details_sheet(xlsx: pd.ExcelWriter, datasets: set[str]):
    """Create dataset details sheet.

    Parameters
    ----------
    xlsx : pd.ExcelWriter
    datasets : set[str]
        list of datasets included in report
    """
    # Keep original order so it matches sheets
    metadata = pd.DataFrame([dataset for dataset in REPORT_DATASETS.values() if dataset["id"] in datasets])
    if "sheet_name" in metadata.columns:
        ix = metadata.sheet_name.isnull() | (metadata.sheet_name == "")
        metadata.loc[ix, "sheet_name"] = metadata.loc[ix].label
    else:
        metadata["sheet_name"] = metadata.label

    metadata.loc[metadata.id.isin([BLUEPRINT["id"]]), "category"] = "Priorities"

    for group in INDICATOR_GROUPS:
        metadata.loc[metadata.id.isin(group["indicators"]), "category"] = f"{group['label']} indicators"

    metadata.loc[
        metadata.id.isin([URBAN_BY_DECADE["id"], PROTECTED_AREAS["id"], PROTECTED_AREAS_POLY["id"]]),
        "category",
    ] = "More information"

    # fill info for indicators from Blueprint
    indicator_ids = [e["id"] for e in INDICATORS]
    ix = metadata.id.isin(indicator_ids)
    metadata.loc[ix, "date"] = BLUEPRINT["date"]
    metadata.loc[ix, "source"] = BLUEPRINT["source"]
    metadata.loc[ix, "citation"] = BLUEPRINT["citation"]

    metadata = metadata[["category", "label", "sheet_name", "source", "date", "description", "citation", "url"]].rename(
        columns={
            "category": "Category",
            "label": "Name",
            "sheet_name": "Sheet",
            "source": "Data source",
            "date": "Date",
            "description": "Description",
            "citation": "Citation",
            "url": "URL",
        }
    )

    write_excel(
        xlsx,
        metadata,
        sheet_name="Data descriptions",
        caption="Details for datasets included in this analysis.",
        column_widths=[18, 24, 18, 24, 8, 64, 48, 40],
    )


def add_metadata_sheet(xlsx: pd.ExcelWriter, name: str | None = None):
    """Add metadata sheet with analysis date and name, if applicable.

    Parameters
    ----------
    xlsx : pd.ExcelWriter
    url : str
        URL to tool
    name : str | None, optional (default None)
        Analysis area name, if any
    """

    metadata = pd.DataFrame(
        [
            {"Label": "Analysis date", "Value": str(date.today())},
            {"Label": "Created using", "Value": "Midwest Conservation Blueprint Explorer"},
        ]
    )
    if name:
        metadata = pd.concat(
            [pd.DataFrame([{"Label": "Analysis area name", "Value": name}]), metadata], ignore_index=True
        )

    write_excel(
        xlsx, metadata, sheet_name="Analysis metadata", caption="Metadata for this analysis.", column_widths=[24, 48]
    )
