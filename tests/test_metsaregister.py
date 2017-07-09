from os.path import abspath, dirname, join

import pytest
from click.testing import CliRunner
import geopandas as gpd

from metsaregister import cli


assert pytest.config.pluginmanager.hasplugin('vcr')


tests_dir = dirname(abspath(__file__))
fixtures_dir = join(tests_dir, 'fixtures')
aoi_path = join(fixtures_dir, 'aoi.geojson')


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
def test_forest_stands(tmpdir):
    runner = CliRunner()
    result_path = str(tmpdir.join('result.geojson'))
    expected_result_path = join(fixtures_dir, 'result_stands.geojson')
    runner.invoke(cli.cli, ['forest_stands', aoi_path, result_path])

    gdf_result = gpd.read_file(result_path)
    gdf_expected = gpd.read_file(expected_result_path)
    assert gdf_expected.equals(gdf_result)


@pytest.mark.vcr
def test_query_layer(tmpdir):
    runner = CliRunner()
    result_path = str(tmpdir.join('result.geojson'))
    expected_result_path = join(fixtures_dir, 'result_layer10.geojson')
    runner.invoke(cli.cli, ['query_layer', aoi_path, '10', result_path])

    gdf_result = gpd.read_file(result_path)
    gdf_expected = gpd.read_file(expected_result_path)
    assert gdf_expected.equals(gdf_result)
