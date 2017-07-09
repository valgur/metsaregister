# -*- coding: utf-8 -*-

from os.path import abspath, dirname, join

import geopandas as gpd
import pytest
from click.testing import CliRunner

from metsaregister import cli, query_forest_stands, query_layer
from metsaregister.cli import _read_aoi

assert pytest.config.pluginmanager.hasplugin('vcr')

tests_dir = dirname(abspath(__file__))
fixtures_dir = join(tests_dir, 'fixtures')
aoi_path = join(fixtures_dir, 'aoi.geojson')
aoi = _read_aoi(aoi_path)


def test_command_line_interface():
    """Test the CLI."""
    runner = CliRunner()
    help_result = runner.invoke(cli.cli, ['--help'])
    assert help_result.exit_code == 0
    assert '--help  Show this message and exit.' in help_result.output


@pytest.mark.vcr
def test_list_layers():
    runner = CliRunner()
    result = runner.invoke(cli.cli, ['list'])
    assert '10\tTeatis' in result.output


@pytest.mark.vcr
def test_forest_stands():
    ret = query_forest_stands(aoi)
    assert len(ret) > 0
    assert len(list(ret)) > 0


@pytest.mark.vcr
def test_forest_stands_cli(tmpdir):
    result_path = str(tmpdir.join('result.geojson'))
    expected_result_path = join(fixtures_dir, 'result_stands.geojson')

    runner = CliRunner()
    runner.invoke(cli.cli, ['forest_stands', aoi_path, result_path])

    gdf_result = gpd.read_file(result_path)
    gdf_expected = gpd.read_file(expected_result_path)
    assert gdf_expected.equals(gdf_result)


@pytest.mark.vcr
def test_query_layer():
    ret = query_layer("POLYGON((675615.4296875 6493875.1953125,675920.1171875 6493875.1953125,675920.1171875 "
                      "6494502.1484375,677742.3828125 6494502.1484375,677742.3828125 6495263.8671875,675615.4296875 "
                      "6495263.8671875,675615.4296875 6493875.1953125))", 10)
    assert len(ret) > 0
    assert len(list(ret)) > 0


@pytest.mark.vcr
def test_query_layer_cli(tmpdir):
    result_path = str(tmpdir.join('result.geojson'))
    expected_result_path = join(fixtures_dir, 'result_layer10.geojson')

    runner = CliRunner()
    runner.invoke(cli.cli, ['query_layer', aoi_path, '10', result_path])

    gdf_result = gpd.read_file(result_path)
    gdf_expected = gpd.read_file(expected_result_path)
    assert gdf_expected.equals(gdf_result)
