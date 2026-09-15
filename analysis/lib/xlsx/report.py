from io import BytesIO

import pandas as pd

from analysis.constants import (
    ANALYSIS_REGION_NAME,
    BLUEPRINT,
    INDICATORS,
    PROTECTED_AREAS,
    PROTECTED_AREAS_POLY,
    REPORT_DATASETS,
    URBAN_BY_DECADE,
)
from analysis.lib.xlsx.basic import add_basic_results_sheet
from analysis.lib.xlsx.metadata import add_data_details_sheet, add_metadata_sheet
from analysis.lib.xlsx.protected_areas import add_protected_areas_poly_sheet
from analysis.lib.xlsx.style import CHAR_PER_WIDTH_UNIT
from analysis.lib.xlsx.summary import add_summary_sheet
from analysis.lib.xlsx.urban import add_urbanization_sheet

basic_datasets = {d["id"] for d in [BLUEPRINT] + INDICATORS + [PROTECTED_AREAS]}

# values in spreadsheet are least to greated by default; this provides custom
# ordering
get_value_order = {d["id"]: lambda x: x[::-1] for d in [BLUEPRINT] + INDICATORS}


def create_report(df: pd.DataFrame, datasets: set[str], name: str | None = None):
    df.index.name = "Analysis unit"
    has_area_outside_region = df.outside_extent_acres.sum() > 1e-2

    name_col_width = max(
        min(pd.Series(df.index).astype("str").apply(len).max() * CHAR_PER_WIDTH_UNIT, 28),
        14,
    )
    area_col_width = max(df.overlap_acres.apply(lambda x: len("{x:,.2f}")).max() * CHAR_PER_WIDTH_UNIT, 10)

    area_label = f"Acres within {ANALYSIS_REGION_NAME} data extent" if has_area_outside_region else "Analysis acres"

    ### Create XLSX file and write to memory buffer
    table_counter = 1
    buffer = BytesIO()
    with pd.ExcelWriter(buffer) as xlsx:
        # Data descriptions sheet
        add_data_details_sheet(xlsx, datasets, table_counter)
        table_counter += 1

        # Summary sheet
        add_summary_sheet(xlsx, df, name_col_width, area_col_width, area_label, has_area_outside_region, table_counter)
        table_counter += 1

        for dataset_id, dataset in REPORT_DATASETS.items():
            if dataset_id not in datasets:
                continue

            # Blueprint, indicators sheets, protected areas (presence)
            if dataset_id in basic_datasets:
                add_basic_results_sheet(
                    xlsx,
                    df,
                    dataset,
                    name_col_width,
                    area_label,
                    table_counter=table_counter,
                    get_value_order=get_value_order.get(dataset_id, None),
                )

            elif dataset_id == PROTECTED_AREAS_POLY["id"]:
                add_protected_areas_poly_sheet(xlsx, df, name_col_width, area_col_width, table_counter=table_counter)

            elif dataset_id == URBAN_BY_DECADE["id"]:
                add_urbanization_sheet(
                    xlsx, df, name_col_width, area_col_width, area_label, table_counter=table_counter
                )

            table_counter += 1

        # Analysis metadata sheet
        add_metadata_sheet(xlsx, table_counter, name)

    # rewind buffer and read data
    buffer.seek(0)
    xlsx_data = buffer.read()

    return xlsx_data
