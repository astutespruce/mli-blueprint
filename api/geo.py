import logging

from pyogrio import list_layers, read_info

from api.settings import MAX_POLYGONS


log = logging.getLogger(__name__)


def list_files(zip):
    """List files in a zipfile, excluding hidden files and directories

    Parameters
    ----------
    zip : ZipFile

    Returns
    -------
    list
        list of file names in the zipfile
    """
    return [f for f in zip.namelist() if "__MACOSX" not in f or ".DS_Store" in f]


def get_geo_files(zip):
    """List the geospatial files in the zipfile.

    Parameters
    ----------
    zip : ZipFile

    Returns
    -------
    list
        list of geospatial files
    """
    return


def get_dataset(zip):
    """Gets singular geospatial dataset and layer for analysis.

    Validates rules:
    - There must be only one data source (.shp or .gdb) in the zip file.
    - There must be only one data layer in that data source.
    - The data source must contain the required files (.prj for shapefile; .dbf is not used so not required)
    - The dataset must contain at least one feature

    Parameters
    ----------
    zip : open ZipFile

    Returns
    -------
    (str, str)
        tuple of geospatial file within zip file, name of layer
    """
    files = set(list_files(zip))
    geo_files = [f for f in list_files(zip) if f.endswith(".shp") or f.endswith(".gdb")]

    num_files = len(geo_files)

    if num_files == 0:
        log.error("Upload zip file does not contain shp or FGDB files")

        raise ValueError("zip file must include a shapefile or FGDB")

    if num_files > 1:
        log.error(
            f"Upload zip file contains {num_files} shp or FGDB files:\n{geo_files}"
        )

        raise ValueError("zip file must include only one shapefile or FGDB")

    filename = geo_files[0]

    if filename.endswith(".shp"):
        missing = []
        for ext in (".prj", ".shx"):
            if filename.replace(".shp", ext) not in files:
                missing.append(ext)

        if missing:
            log.error(f"Upload zip file contains .shp but not {','.join(missing)}")
            raise ValueError("zip file must include .shp, .prj, and .shx files")

    # Validate that dataset is a polygon and has only a single layer
    dataset = f"/vsizip/{zip.fp.name}/{filename}"
    layers = list_layers(dataset)

    if layers.shape[0] > 1:
        log.error(f"Upload data source contains multiple data layers\n{layers}")
        raise ValueError("data source must contain only one data layer")

    if "Polygon" not in layers[0, 1]:
        log.error(f"Upload data source is not a polygon: {layers[0,1]}")
        raise ValueError("data source must be a Polygon type")

    # Validate that that layer has at least one feature but doesn't have too many
    # features
    num_features = read_info(dataset, layers[0, 0])["features"]
    if num_features == 0:
        log.error("Upload data source does not contain any features")
        raise ValueError("data source must contain at least one feature")

    elif num_features > MAX_POLYGONS:
        log.error("Upload data source contains too many features")
        raise ValueError(
            f"data source contains too many features: {num_features:,} (must be <{MAX_POLYGONS:,}).  Please select a smaller subset of features or preprocess this dataset to reduce the number of individual features (e.g., dissolve adjacent boundaries)."
        )

    return filename, layers[0, 0]
