# -*- coding: utf-8 -*-

"""Console script for metsaregister."""

from __future__ import print_function

import click
import geopandas as gpd
from shapely.ops import cascaded_union

import metsaregister


def _read_aoi(aoi_path):
    gdf = gpd.read_file(aoi_path)
    return cascaded_union(list(gdf.geometry)).wkt


def _add_crs(json):
    return json.replace(
        '{',
        '{\n"crs": { "type": "name", "properties": { "name": "urn:ogc:def:crs:EPSG::3301" } }, ',
        1
    )


@click.group()
def cli():
    return


@cli.command(name="list", help="List available layers and their IDs")
def list_layers():
    layers = metsaregister.get_layers()
    for name, id in layers.items():
        print(id, name, sep='\t')


@cli.command(help="""Get any layer's features intersecting with a given AOI.

Takes a vector file containing the area of interest as input. Must be in L-EST97 CRS.

For a list of available layers and their IDs see the 'list' command.

The result is saved as a GeoJSON file.""")
@click.argument('aoi', type=str)
@click.argument('layer_id', type=int)
@click.argument('out_path', type=str)
def get_layer(aoi, layer_id, out_path):
    aoi = _read_aoi(aoi)
    gdf = metsaregister.query_layer(aoi, layer_id)
    with open(out_path, 'w', encoding='utf8') as f:
        f.write(_add_crs(gdf.to_json()))


@cli.command(help="""Fetch and save forest stands' information for a given AOI.

Takes a vector file containing the area of interest as input. Must be in L-EST97 CRS.

The result is saved as a GeoJSON file.""")
@click.argument('aoi', type=str)
@click.argument('out_path', type=str)
@click.option('--wait', default=0.5, type=float,
              help="Time to wait in seconds between querying each stand's information "
                   "to not overload the server. Defaults to 0.5 s.")
def forest_stands(aoi, out_path, wait):
    aoi = _read_aoi(aoi)
    gdf = metsaregister.query_forest_stands(aoi, wait)
    with open(out_path, 'w', encoding='utf8') as f:
        f.write(_add_crs(gdf.to_json()))


@cli.command(help="""Fetch and save forest notifications' information for a given AOI.

Takes a vector file containing the area of interest as input. Must be in L-EST97 CRS.

The result is saved as a GeoJSON file.""")
@click.argument('aoi', type=str)
@click.argument('out_path', type=str)
@click.option('--wait', default=0.5, type=float,
              help="Time to wait in seconds between querying each stand's information "
                   "to not overload the server. Defaults to 0.5 s.")
def forest_notifications(aoi, out_path, wait):
    aoi = _read_aoi(aoi)
    gdf = metsaregister.query_forest_notifications(aoi, wait)
    with open(out_path, 'w', encoding='utf8') as f:
        f.write(_add_crs(gdf.to_json()))


if __name__ == "__main__":
    cli()
