import pandas as pd

from analysis.constants import ANALYSIS_REGION_NAME
from analysis.lib.xlsx.style import CHAR_PER_WIDTH_UNIT, add_caption, set_cell_styles, set_column_widths


def add_summary_sheet(
    xlsx: pd.ExcelWriter,
    df: pd.DataFrame,
    name_col_width: float,
    area_col_width: float,
    area_label: str,
    has_area_outside_region: bool,
    table_counter: int,
):
    """Create summary sheet for XLSX report, with the area and other summary
    statistics for each analysis unit.

    Parameters
    ----------
    xlsx : pd.ExcelWriter
    df : pd.DataFrame
        results DataFrame
    name_col_width : float
        width of name column
    area_col_width : float
        width of area column
    area_label : str
        area column label
    has_area_outside_region : bool
        True if there is area in any of the analysis regions outside analysis region
    """
    sheet_name = "Summary"

    pixel_col_width = max(df.pixels.apply(lambda x: len("{x:,}")).max() * CHAR_PER_WIDTH_UNIT, 12)

    cols = ["acres", "overlap_acres"]
    col_widths = [name_col_width, area_col_width, area_col_width]
    area_columns = [1, 2]
    if has_area_outside_region:
        cols.append("outside_extent_acres")
        col_widths.append(16)
        area_columns.append(3)

    cols.extend(["pixels", "count", "states"])
    col_widths.extend([pixel_col_width, 16, 20])
    # NOTE: pixels col is treated as an area col so it can be formated with commas
    area_columns.append(4 if has_area_outside_region else 3)

    df[cols].reset_index().rename(
        columns={
            "acres": "GIS acres",
            "pixels": "Number of 30m pixels in analysis unit",
            "overlap_acres": area_label + " (rasterized to 30m pixels)",
            "outside_extent_acres": f"Acres outside {ANALYSIS_REGION_NAME} data extent (rasterized to 30m pixels)",
            "count": "Number of distinct areas in analysis unit",
            "states": "State(s)",
        }
    ).to_excel(xlsx, sheet_name=sheet_name, index=False)
    ws = xlsx.sheets[sheet_name]
    set_cell_styles(ws, area_columns=area_columns)
    set_column_widths(ws, col_widths)

    add_caption(ws, table_counter, "Summary of analysis units included in this analysis.")
