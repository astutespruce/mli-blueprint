from pathlib import Path

import pyarrow.dataset as pa
import pyarrow.compute as pc


data_dir = Path("data")
huc12_filename = data_dir / "inputs/summary_units/huc12.feather"
marine_filename = data_dir / "inputs/summary_units/marine_hex.feather"


def read_unit_from_feather(filename, unit_id, columns=None):
    """Read a summary unit from a Feather file, returning rows that match unit_id

    Parameters
    ----------
    filename : str or Path
    unit_id : str
    columns : list-like, optional (default: None)
        list of columns to extract from Feather

    Returns
    -------
    DataFrame
    """
    src = pa.dataset(filename, format="feather")
    return (
        src.to_table(columns=columns, filter=pc.field("id") == unit_id)
        .to_pandas()
        .set_index("id")
    )
