import pandas as pd

from analysis.constants import PROTECTED_AREAS_POLY
from analysis.lib.xlsx.writer import write_excel


def add_protected_areas_poly_sheet(
    xlsx: pd.ExcelWriter, df: pd.DataFrame, name_col_width: float, area_col_width: float
):
    dataset = PROTECTED_AREAS_POLY

    # transform data into one row per per protected area per analysis unit
    protected_areas = []
    breaks = []
    counter = 0
    col = dataset["id"]
    for id, row in df.iterrows():
        if len(row.get(col, [])):
            for pa in row[col]:
                protected_areas.append([id, row.acres, pa["acres"], pa["acres"] / row.acres, pa["name"], pa["owner"]])
                counter += 1
        else:
            protected_areas.append([id, row.acres, 0, 0, "no protected areas at this location", ""])
            counter += 1

        breaks.append(counter)

    protected_areas = pd.DataFrame(
        protected_areas,
        columns=[df.index.name, "GIS acres", "Overlap acres", "Overlap percent", "Name", "Owner"],
    )

    column_widths = [name_col_width, area_col_width, area_col_width, area_col_width, 40, 30]
    write_excel(
        xlsx,
        protected_areas,
        sheet_name=dataset["sheet_name"],
        caption=dataset["caption"] + ".",
        column_widths=column_widths,
        area_columns=[1, 2],
        percent_columns=[3],
        # only include breaks if they are not incremental
        breaks=None if breaks == list(range(len(df))) else breaks,
    )
