# ruff: noqa

from analysis.lib.geometry.aggregate import (
    dissolve,
    find_contiguous_groups,
    union_or_combine,
)
from analysis.lib.geometry.clean import make_valid
from analysis.lib.geometry.conversion import to_dict, to_dict_all
from analysis.lib.geometry.crs import to_crs
from analysis.lib.geometry.polygons import get_holes, drop_all_holes
