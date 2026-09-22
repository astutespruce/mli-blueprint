import pandas as pd

from analysis.lib.xlsx.style import CHAR_PER_WIDTH_UNIT, add_caption, set_cell_styles, set_column_widths


def get_value_columns(values):
    return [f"{v['label'].replace(' (', '\n(')}\n(acres)" for v in values]


def add_basic_results_sheet(
    xlsx: pd.ExcelWriter,
    df: pd.DataFrame,
    dataset: dict,
    name_col_width: float,
    area_label: str,
    outside_area_label: str,
    table_counter: int,
    get_value_order=None,
):
    """Add a sheet for one of the Blueprint datasets (Blueprint, indicators)
    or other simple raster results dataset.

    Parameters
    ----------
    xlsx : pd.ExcelWriter
    df : pd.DataFrame
    dataset : dict
        dataset object with info
    name_col_width : float
        width of name column
    area_label : str
        name of analysis area acres column
    outside_area_label : str
        name of outside analysis area acres column
    table_counter : int
        table counter for this table, 1-based
    get_value_order : function, optional (default: None)
        if defined, function that returns value columns in correct order
    """

    sheet_name = dataset.get("sheet_name", None) or dataset["label"]

    if len(sheet_name) > 31:
        print(f"WARNING: Sheet name too long: {sheet_name}")

    values = dataset["values"]
    caption = dataset["caption"] + "."

    value_label = dataset.get("valueLabel", None)
    if value_label:
        caption += f"  Values show {value_label[0].lower()}{value_label[1:]}."

    nodata_label = dataset.get("nodata_label", "Outside extent of this dataset") + "\n(acres)"

    value_columns = get_value_columns(values)
    col_width = min(max([len(c) for c in value_columns]) * CHAR_PER_WIDTH_UNIT, 18)

    # split list into columns
    tmp = df[dataset["id"]].apply(pd.Series)
    tmp.columns = value_columns
    tmp = df[["rasterized_acres", "overlap_acres", "outside_extent_acres", "outside_extent_percent"]].join(tmp)

    # calculate area outside this dataset
    tmp["outside_dataset_acres"] = tmp.overlap_acres - tmp[value_columns].sum(axis=1)
    # remove small rounding-related errors
    tmp.loc[tmp.outside_dataset_acres < 0, "outside_dataset_acres"] = 0
    # NOTE: percents are actually proportions formatted as percents
    tmp["outside_dataset_percent"] = tmp.outside_dataset_acres / tmp.rasterized_acres

    # reorder columns
    if get_value_order is not None:
        value_columns = get_value_order(value_columns)

    percent_columns = [col.replace("(acres)", "(percent)") for col in value_columns]
    for value_col, percent_col in zip(value_columns, percent_columns):
        tmp[percent_col] = tmp[value_col] / tmp.rasterized_acres

    tmp = tmp[
        ["overlap_acres", "outside_extent_acres", "outside_dataset_acres"]
        + value_columns
        + ["outside_extent_percent", "outside_dataset_percent"]
        + percent_columns
    ]

    # drop columns if no area present outside extent or dataset
    has_area_outside_extent = tmp.outside_extent_acres.max() > 1e-2
    if not has_area_outside_extent:
        tmp = tmp.drop(columns=["outside_extent_acres", "outside_extent_percent"])

    has_area_outside_dataset = tmp.outside_dataset_acres.max() > 1e-2
    if not has_area_outside_dataset:
        tmp = tmp.drop(columns=["outside_dataset_acres", "outside_dataset_percent"])

    tmp = tmp.rename(
        columns={
            "overlap_acres": area_label,
            "outside_extent_acres": outside_area_label,
            "outside_extent_percent": outside_area_label.replace("(acres)", "(percent)"),
            "outside_dataset_acres": nodata_label,
            "outside_dataset_percent": nodata_label.replace("(acres)", "(percent)"),
        }
    )

    tmp.reset_index().to_excel(xlsx, sheet_name=sheet_name, index=False)

    ws = xlsx.sheets[sheet_name]

    set_column_widths(ws, [name_col_width] + ([col_width] * len(tmp.columns)))

    area_col_offset = 1
    num_area_cols = len(value_columns) + 1 + int(has_area_outside_extent) + int(has_area_outside_dataset)

    set_cell_styles(
        ws,
        area_columns=range(area_col_offset, area_col_offset + num_area_cols),
        percent_columns=range(area_col_offset + num_area_cols, area_col_offset + num_area_cols + num_area_cols),
        add_percent_divider=True,
    )

    add_caption(ws, table_counter, caption)
