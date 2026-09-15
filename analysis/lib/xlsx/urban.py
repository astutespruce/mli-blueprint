import pandas as pd

from analysis.constants import URBAN_BY_DECADE, URBAN_YEARS
from analysis.lib.xlsx.style import add_caption, set_cell_styles, set_column_widths

value_columns = (
    ["Urban in 2021\n(acres)"]
    + [f"{year} projected extent\n(acres)" for year in URBAN_YEARS]
    + ["Not projected to urbanize by 2100\n(acres)"]
)


def add_urbanization_sheet(
    xlsx: pd.ExcelWriter,
    df: pd.DataFrame,
    name_col_width: float,
    area_col_width: float,
    area_label: str,
    table_counter: int,
):
    """Add urbanization sheet.

    Parameters
    ----------
    xlsx : pd.ExcelWriter
    df : pd.DataFrame
    name_col_width : float
        width of name column
    area_col_width : float
        width of area column
    area_label : str
        name of analysis area acres column
    table_counter : int
    """
    dataset = URBAN_BY_DECADE
    sheet_name = dataset["label"]
    caption = dataset["caption"] + "."
    nodata_label = dataset.get(
        "nodata_label",
        "Outside extent of this dataset",
    )

    columns = value_columns + ["outside_acres"]

    # convert values to columns
    urban = df[["overlap_acres"]].join(df[URBAN_BY_DECADE["id"]].apply(pd.Series))
    urban.columns = ["overlap_acres"] + columns
    # move nodata to left
    urban = urban[["overlap_acres", "outside_acres"] + value_columns]
    if urban.outside_acres.max() < 1e-2:
        urban = urban.drop(columns=["outside_acres"])

    urban.rename(columns={"overlap_acres": area_label, "outside_acres": nodata_label}).reset_index().to_excel(
        xlsx, sheet_name=sheet_name, index=False
    )

    ws = xlsx.sheets[sheet_name]
    set_column_widths(ws, [name_col_width, area_col_width] + ([18] * (len(urban.columns) - 1)))
    set_cell_styles(ws, area_columns=range(1, len(urban.columns) + 3))

    add_caption(ws, table_counter, caption)
