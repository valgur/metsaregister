# -*- coding: utf-8 -*-

"""Console script for metsaregister."""

import click
import geopandas as gpd
from shapely.ops import cascaded_union

import metsaregister


def _read_aoi(aoi_path):
    gdf = gpd.read_file(aoi_path)
    return cascaded_union(list(gdf.geometry)).wkt


@click.group()
def cli():
    return


@cli.command(name="list", help="List available layers and their IDs")
def list_layers():
    layers = metsaregister.get_layers()
    for name, id in layers.items():
        print(id, name, sep='\t')


@cli.command(help="""Query layer's features intersecting with a given AOI.

Takes a vector file containing the area of interest as input. Must be in L-EST97 CRS.

For a list of available layers and their IDs see the 'list' command.

The result is saved as a GeoJSON file.""")
@click.argument('aoi', type=str)
@click.argument('layer_id', type=str)
@click.argument('out_path', type=str)
def query_layer(aoi, layer_id, out_path):
    aoi = _read_aoi(aoi)
    gdf = metsaregister.query_layer(aoi, layer_id)
    with open(out_path, 'w', encoding='utf8') as f:
        f.write(gdf.to_json())


@cli.command(help="""Query and save forest stands' information for a given AOI.

Takes a vector file containing the area of interest as input. Must be in L-EST97 CRS.

The result is saved as a GeoJSON file.""")
@click.argument('aoi', type=str)
@click.argument('out_path', type=str)
def forest_stands(aoi, out_path):
    aoi = _read_aoi(aoi)
    gdf = metsaregister.query_forest_stands(aoi)
    with open(out_path, 'w', encoding='utf8') as f:
        f.write(gdf.to_json())


if __name__ == "__main__":
    cli()
