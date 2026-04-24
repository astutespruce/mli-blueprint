# Midwest Conservation Blueprint Data Preparation

Source data are stored in `source_data`; see associated README files for data sources there.

Where possible, data are used from the Southeast Blueprint Explorer project
in `../secas-blueprint/source_data`.

## Data processing steps

1. `prepare_boundaries.py`: Prepare Midwest region boundary and mask for analysis and mapping
2. `prepare_summary_units.py`: Compile and prepare HUC12 summary units for analysis and mapping
3. `prepare_protected_areas.py`: Prepare PAD-US protected areas data for analysis and mapping
4. `prepare_blueprint.py`: Prepare Midwest Blueprint, corridors, and indicators for analysis and mapping
5. `prepare_nlcd.py`: Prepare NLCD data
6. `prepare_urban.py`: Prepare urbanization data
7. `tabulate_summary_units.py`: Tabulate Blueprint, indicators, and other data layers by HUC12
8. `package_unit_data.py`: Restructure data for HUC12 to attach to boundary datasets for map tiles
9. `tiles/create_vector_tiles.py`: Create vector tiles from HUC12, blueprint region and mask, input areas, and protected areas
10. `tiles/encode_pixel_layers.py`: Stack and encode pixel layers for data tiles
11. `tiles/create_raster_tiles.sh`: Create Blueprint and data tiles

Note: once tiles are rendered, they are moved to `secas-docker/tiles` directory.
