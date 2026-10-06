import pandas as pd

from analysis.constants import ANALYSIS_REGION_NAME
from analysis.lib.xlsx.style import CHAR_PER_WIDTH_UNIT
from analysis.lib.xlsx.writer import write_excel


def add_summary_sheet(xlsx: pd.ExcelWriter, df: pd.DataFrame, name_col_width: float, has_area_outside_region: bool):
    """Create summary sheet for XLSX report, with the area and other summary
    statistics for each analysis unit.

    Parameters
    ----------
    xlsx : pd.ExcelWriter
    df : pd.DataFrame
        results DataFrame
    name_col_width : float
        width of name column
    has_area_outside_region : bool
        True if there is area in any of the analysis regions outside analysis region
    """
    sheet_name = "Summary"

    pixel_col_width = max(df.pixels.apply(lambda x: len("{x:,}")).max() * CHAR_PER_WIDTH_UNIT, 12)

    cols = ["acres", "overlap_acres"]
    column_widths = [name_col_width, 16, 16]
    area_columns = [1, 2]
    if has_area_outside_region:
        cols.append("outside_extent_acres")
        column_widths.append(16)
        area_columns.append(3)

    cols.extend(["pixels", "count", "states"])
    column_widths.extend([pixel_col_width, 16, 20])
    # NOTE: pixels col is treated as an area col so it can be formated with commas
    area_columns.append(4 if has_area_outside_region else 3)

    df = (
        df[cols]
        .reset_index()
        .rename(
            columns={
                "acres": "GIS acres",
                "pixels": "Number of 30m pixels in analysis unit",
                "overlap_acres": f"Acres within {ANALYSIS_REGION_NAME} data extent (rasterized to 30m pixels)"
                if has_area_outside_region
                else "Analysis acres (rasterized to 30m pixels)",
                "outside_extent_acres": f"Acres outside {ANALYSIS_REGION_NAME} data extent (rasterized to 30m pixels)",
                "count": "Number of distinct areas in analysis unit",
                "states": "State(s)",
            }
        )
    )

    write_excel(
        xlsx,
        df,
        sheet_name=sheet_name,
        caption="Summary of analysis units included in this analysis.",
        column_widths=column_widths,
        area_columns=area_columns,
    )
