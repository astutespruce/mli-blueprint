import pandas as pd

from analysis.constants import URBAN_BY_DECADE, URBAN_YEARS
from analysis.lib.xlsx.writer import write_excel

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
    outside_area_label: str,
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
    """
    dataset = URBAN_BY_DECADE
    nodata_label = "Outside extent of this dataset\n(acres)"

    # convert values to columns
    urban = df[["rasterized_acres", "overlap_acres", "outside_extent_acres", "outside_extent_percent"]].join(
        df[URBAN_BY_DECADE["id"]].apply(pd.Series)
    )
    urban.columns = (
        ["rasterized_acres", "overlap_acres", "outside_extent_acres", "outside_extent_percent"]
        + value_columns
        + ["outside_dataset_acres"]
    )

    # calculate percents
    urban["outside_dataset_percent"] = urban.outside_dataset_acres / urban.rasterized_acres
    for col in value_columns:
        urban[col.replace("(acres)", "(percent)")] = urban[col] / urban.rasterized_acres

    # move nodata to left
    urban = urban[
        ["overlap_acres", "outside_extent_acres", "outside_dataset_acres"]
        + value_columns
        + ["outside_extent_percent", "outside_dataset_percent"]
        + [col.replace("(acres)", "(percent)") for col in value_columns]
    ]

    has_area_outside_extent = urban.outside_extent_acres.max() > 1e-2
    if not has_area_outside_extent:
        urban = urban.drop(columns=["outside_extent_acres", "outside_extent_percent"])

    has_area_outside_dataset = urban.outside_dataset_acres.max() > 1e-2
    if not has_area_outside_dataset:
        urban = urban.drop(columns=["outside_dataset_acres", "outside_dataset_percent"])

    urban = urban.rename(
        columns={
            "overlap_acres": area_label,
            "outside_extent_acres": outside_area_label,
            "outside_extent_percent": outside_area_label.replace("(acres)", "(percent)"),
            "outside_dataset_acres": nodata_label,
            "outside_dataset_percent": nodata_label.replace("(acres)", "(percent)"),
        }
    ).reset_index()

    area_col_offset = 1
    num_area_cols = len(value_columns) + int(has_area_outside_extent) + int(has_area_outside_dataset) + 1

    column_widths = [name_col_width, area_col_width] + ([18] * (len(urban.columns) - 2))
    area_columns = list(range(area_col_offset, area_col_offset + num_area_cols))
    percent_columns = list(range(area_col_offset + num_area_cols, area_col_offset + num_area_cols + num_area_cols))
    write_excel(
        xlsx,
        urban,
        sheet_name=dataset["label"],
        caption=dataset["caption"] + ".",
        column_widths=column_widths,
        area_columns=area_columns,
        percent_columns=percent_columns,
        add_percent_divider=True,
    )
