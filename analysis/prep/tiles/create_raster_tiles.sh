#!/bin/bash

mkdir -p tiles/tmp

function rastertiler () {
    ./../rastertiler-rs/target/release/rastertiler "$@"
}

echo "Rendering Blueprint tiles"
rastertiler render data/inputs/blueprint.tif tiles/tmp/blueprint_z3_6.mbtiles -s 512 -n blueprint --colormap "1:#89bf7c,2:#388c3a,3:#0f662c,4:#00441b" -Z 3 -z 6
rastertiler render data/inputs/blueprint.tif tiles/tmp/blueprint_z7_14.mbtiles -s 512 -n blueprint --colormap "1:#89bf7c,2:#388c3a,3:#0f662c,4:#00441b" -Z 7 -z 14 --disable-overviews
rastertiler merge tiles/tmp/blueprint_z3_6.mbtiles tiles/tmp/blueprint_z7_14.mbtiles tiles/midwest_blueprint.mbtiles


# IMPORTANT: all the data tiles need to be rendered without overviews, which cause significant distortion (even at very low overview factors like 2)

echo "Rendering pixel layer 0"
rastertiler render data/for_tiles/midwest_pixel_layers_0.tif tiles/midwest_pixel_layers_0.mbtiles -s 512 -n midwest_pixel_layers_0 -Z 3 -z 14 --disable-overviews

echo "Rendering pixel layer 1"
rastertiler render data/for_tiles/midwest_pixel_layers_1.tif tiles/midwest_pixel_layers_1.mbtiles -s 512 -n midwest_pixel_layers_1 -Z 3 -z 14 --disable-overviews

echo "Rendering pixel layer 2"
rastertiler render data/for_tiles/midwest_pixel_layers_2.tif tiles/midwest_pixel_layers_2.mbtiles -s 512 -n midwest_pixel_layers_2 -Z 3 -z 14 --disable-overviews

echo "Rendering pixel layer 3"
rastertiler render data/for_tiles/midwest_pixel_layers_3.tif tiles/midwest_pixel_layers_3.mbtiles -s 512 -n midwest_pixel_layers_3 -Z 3 -z 14 --disable-overviews

echo "Rendering pixel layer 4"
rastertiler render data/for_tiles/midwest_pixel_layers_4.tif tiles/midwest_pixel_layers_4.mbtiles -s 512 -n midwest_pixel_layers_4 -Z 3 -z 14 --disable-overviews

