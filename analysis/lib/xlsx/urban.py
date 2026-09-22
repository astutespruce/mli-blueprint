import pandas as pd

from analysis.constants import URBAN_BY_DECADE, URBAN_YEARS
from analysis.lib.xlsx.style import add_caption, set_cell_styles, set_column_widths

value_columns = (
    ["Urban in 2021\n(acres)"]
    + [f"{year} projected extent\n(acres)" for year in URBAN_YEARS]
    + ["Not projected to urbanize by 2100\n(acres)"]
)
percent_columns = [col.replace("(acres)", "(percent)") for col in value_columns]


def add_urbanization_sheet(
    xlsx: pd.ExcelWriter,
    df: pd.DataFrame,
    name_col_width: float,
    area_col_width: float,
    area_label: str,
    outside_area_label: str,
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
    outside_area_label : str
        name of outside analysis area acres column
    table_counter : int
    """
    dataset = URBAN_BY_DECADE
    sheet_name = dataset["label"]
    caption = dataset["caption"] + "."
    nodata_label = (
        dataset.get(
            "nodata_label",
            "Outside extent of this dataset",
        )
        + "\n(acres)"
    )

    columns = value_columns + ["outside_dataset_acres"]

    # convert values to columns
    urban = df[["rasterized_acres", "overlap_acres", "outside_extent_acres", "outside_extent_percent"]].join(
        df[URBAN_BY_DECADE["id"]].apply(pd.Series)
    )
    urban.columns = ["rasterized_acres", "overlap_acres", "outside_extent_acres", "outside_extent_percent"] + columns

    # calculate percents
    urban["outside_dataset_percent"] = urban.outside_dataset_acres / urban.rasterized_acres
    for col in value_columns:
        urban[col.replace("(acres)", "(percent)")] = urban[col] / urban.rasterized_acres

    # move nodata to left
    urban = urban[
        ["overlap_acres", "outside_extent_acres", "outside_dataset_acres"]
        + value_columns
        + ["outside_extent_percent", "outside_dataset_percent"]
        + percent_columns
    ]

    has_area_outside_extent = urban.outside_extent_acres.max() > 1e-2
    if not has_area_outside_extent:
        urban = urban.drop(columns=["outside_extent_acres", "outside_extent_percent"])

    has_area_outside_dataset = urban.outside_dataset_acres.max() > 1e-2
    if not has_area_outside_dataset:
        urban = urban.drop(columns=["outside_dataset_acres", "outside_dataset_percent"])

    urban.rename(
        columns={
            "overlap_acres": area_label,
            "outside_extent_acres": outside_area_label,
            "outside_extent_percent": outside_area_label.replace("(acres)", "(percent)"),
            "outside_dataset_acres": nodata_label,
            "outside_dataset_percent": nodata_label.replace("(acres)", "(percent)"),
        }
    ).reset_index().to_excel(xlsx, sheet_name=sheet_name, index=False)

    ws = xlsx.sheets[sheet_name]
    set_column_widths(ws, [name_col_width, area_col_width] + ([18] * (len(urban.columns) - 1)))

    area_col_offset = 1
    num_area_cols = len(value_columns) + 1 + int(has_area_outside_extent) | int(has_area_outside_dataset)

    set_cell_styles(
        ws,
        area_columns=range(area_col_offset, area_col_offset + num_area_cols),
        percent_columns=range(area_col_offset + num_area_cols, area_col_offset + num_area_cols + num_area_cols),
        add_percent_divider=True,
    )

    add_caption(ws, table_counter, caption)
