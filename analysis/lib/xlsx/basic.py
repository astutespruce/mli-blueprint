import pandas as pd

from analysis.constants import INDICATORS_INDEX
from analysis.lib.xlsx.style import (
    CHAR_PER_WIDTH_UNIT,
    add_caption,
    add_good_condition_row,
    set_cell_styles,
    set_column_widths,
)


def get_value_columns(values):
    return [f"{v['label'].replace(' (', '\n(')}\n(acres)" for v in values]


def add_basic_results_sheet(
    xlsx: pd.ExcelWriter,
    df: pd.DataFrame,
    dataset: dict,
    name_col_width: float,
    area_label: str,
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

    # good threshold is only applicable to indicators
    if dataset["id"] in INDICATORS_INDEX:
        good_threshold = dataset.get("goodThreshold", None)
        if good_threshold:
            caption += "  Good condition thresholds reflect the range of indicator values that occur in healthy, functioning ecosystems."
        else:
            caption += "  A good condition threshold is not yet defined for this indicator."

    value_label = dataset.get("valueLabel", None)
    if value_label:
        caption += f"  Values show {value_label[0].lower()}{value_label[1:]}."

    nodata_label = dataset.get("nodata_label", "Outside extent of this dataset")

    value_columns = get_value_columns(values)
    col_width = min(max([len(c) for c in value_columns]) * CHAR_PER_WIDTH_UNIT, 18)

    # split list into columns
    tmp = df[dataset["id"]].apply(pd.Series)
    tmp.columns = value_columns
    tmp = df[["overlap_acres"]].join(tmp)

    # calculate area outside
    tmp["outside_acres"] = tmp.overlap_acres - tmp[value_columns].sum(axis=1)
    # remove small rounding-related errors
    tmp.loc[tmp.outside_acres < 0, "outside_acres"] = 0

    # reorder columns
    if get_value_order is not None:
        value_columns = get_value_order(value_columns)
    tmp = tmp[["overlap_acres", "outside_acres"] + value_columns]

    # drop outside indicator col
    has_area_outside = tmp.outside_acres.max() > 1e-2
    if not has_area_outside:
        tmp = tmp.drop(columns=["outside_acres"])

    tmp.rename(columns={"overlap_acres": area_label, "outside_acres": nodata_label}).reset_index().to_excel(
        xlsx, sheet_name=sheet_name, index=False
    )

    ws = xlsx.sheets[sheet_name]
    set_column_widths(ws, [name_col_width] + ([col_width] * len(tmp.columns)))
    set_cell_styles(ws, area_columns=range(1, len(tmp.columns) + 3))

    add_caption(ws, table_counter, caption)

    if dataset["id"] in INDICATORS_INDEX and good_threshold:
        # NOTE: this only applies to indicators, which are always in greatest to least order
        offset = 3 if has_area_outside else 2
        pos = [v["value"] for v in values[::-1]].index(good_threshold) + 1
        add_good_condition_row(ws, offset, offset + len(values), break_col=pos)
