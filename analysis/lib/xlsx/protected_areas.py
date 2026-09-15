import pandas as pd

from analysis.constants import PROTECTED_AREAS_POLY
from analysis.lib.xlsx.style import add_caption, set_cell_styles, set_column_widths


def add_protected_areas_poly_sheet(
    xlsx: pd.ExcelWriter, df: pd.DataFrame, name_col_width: float, area_col_width: float, table_counter: int
):
    dataset = PROTECTED_AREAS_POLY
    sheet_name = dataset["sheet_name"]
    caption = dataset["caption"] + "."

    # transform data into one row per per protected area per analysis unit
    protected_areas = []
    breaks = []
    counter = 0
    col = dataset["id"]
    for id, row in df.iterrows():
        if len(row.get(col, [])):
            for pa in row[col]:
                protected_areas.append([id, f"{row.acres:.2f}", f"{pa['acres']:.2f}", pa["name"], pa["owner"]])
        else:
            protected_areas.append([id, f"{row.acres:.2f}", "0", "no protected areas at this location", ""])
            counter += 1

        breaks.append(counter)

    protected_areas = pd.DataFrame(
        protected_areas,
        columns=[df.index.name, "GIS acres", "Overlap acres", "Name", "Owner"],
    )
    protected_areas.to_excel(xlsx, sheet_name=sheet_name, index=False)
    ws = xlsx.sheets[sheet_name]

    set_column_widths(ws, [name_col_width, area_col_width, area_col_width, 40, 30])
    set_cell_styles(ws)

    add_caption(ws, table_counter, caption)
