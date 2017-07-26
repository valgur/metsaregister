# -*- coding: utf-8 -*-

import math
from os.path import abspath, dirname, join

import geopandas as gpd
import pytest
from click.testing import CliRunner

from metsaregister import cli, get_info, get_layers, parse_forest_notifications, \
    query_forest_notifications, query_forest_stands, query_layer
from metsaregister.cli import _read_aoi

assert pytest.config.pluginmanager.hasplugin('vcr')

tests_dir = dirname(abspath(__file__))
fixtures_dir = join(tests_dir, 'fixtures')
aoi_path = join(fixtures_dir, 'aoi.geojson')
aoi_empty_path = join(fixtures_dir, 'aoi_empty.geojson')
aoi_notifications_path = join(fixtures_dir, 'aoi_notifications.geojson')
aoi = _read_aoi(aoi_path)
aoi_notifications = _read_aoi(aoi_notifications_path)
empty_aoi = "POLYGON ((30 10, 40 40, 20 40, 10 20, 30 10))"


@pytest.fixture(scope='module')
def vcr_config():
    bad_headers = ["Authorization", "Set-Cookie", "Cookie", "Date", "Expires", "Transfer-Encoding"]

    def scrub_response(response):
        for header in bad_headers:
            if header in response["headers"]:
                del response["headers"][header]
        return response

    return dict(
        match_on=['uri', 'body'],
        filter_headers=bad_headers,
        before_record_response=scrub_response
    )


@pytest.mark.vcr
def test_get_layers():
    ret = get_layers()
    assert len(ret) > 10
    assert all(isinstance(x, int) for x in ret.values())
    assert ret['Teatis'] == 10


@pytest.mark.vcr
def test_forest_stands():
    ret = query_forest_stands(aoi, 0.1)
    assert ret.crs == {'init': 'epsg:3301'}
    assert ret.shape[0] > 0
    assert ret.shape[1] > 0
    assert not all(ret.dtypes == object)


@pytest.mark.vcr
def test_forest_stands_empty_response():
    ret = query_forest_stands(empty_aoi)
    assert ret.crs == {'init': 'epsg:3301'}
    assert ret.shape[0] == 0
    assert ret.shape[1] == 0


@pytest.mark.vcr
def test_parse_forest_notifications():
    info = get_info('info_teatis.php?too_id=3533008401')
    ret = parse_forest_notifications(info)
    assert len(ret) > 0
    assert ret['Töö'] == 'lageraie'
    assert ret['Maht (tm)'] == 132

    info = info.replace('132 tm', 'xxx')
    ret = parse_forest_notifications(info)
    assert len(ret) > 0
    assert ret['Töö'] == 'lageraie xxx'
    assert math.isnan(ret['Maht (tm)'])


@pytest.mark.vcr
def test_forest_notifications():
    ret = query_forest_notifications(aoi_notifications, 0.1)
    assert ret.crs == {'init': 'epsg:3301'}
    assert ret.shape[0] > 0
    assert ret.shape[1] > 0
    assert not all(ret.dtypes == object)


@pytest.mark.vcr
def test_forest_notifications_empty_response():
    ret = query_forest_notifications(empty_aoi)
    assert ret.crs == {'init': 'epsg:3301'}
    assert ret.shape[0] == 0
    assert ret.shape[1] == 0


@pytest.mark.vcr
def test_query_layer():
    ret = query_layer(
        "POLYGON((675615.4296875 6493875.1953125,675920.1171875 6493875.1953125,675920.1171875 "
        "6494502.1484375,677742.3828125 6494502.1484375,677742.3828125 6495263.8671875,675615.4296875 "
        "6495263.8671875,675615.4296875 6493875.1953125))", 10)
    assert ret.crs == {'init': 'epsg:3301'}
    assert len(ret) > 0
    assert len(list(ret)) > 0


def test_command_line_interface():
    runner = CliRunner()
    help_result = runner.invoke(cli.cli, ['--help'])
    assert help_result.exit_code == 0
    assert '--help  Show this message and exit.' in help_result.output


@pytest.mark.vcr
def test_list_layers_cli():
    runner = CliRunner()
    result = runner.invoke(cli.cli, ['list'])
    assert result.exit_code == 0
    assert '10\tTeatis' in result.output


@pytest.mark.vcr
def test_query_layer_cli(tmpdir):
    result_path = str(tmpdir.join('result.geojson'))
    expected_result_path = join(fixtures_dir, 'result_layer10.geojson')

    runner = CliRunner()
    r = runner.invoke(cli.cli, ['get_layer', aoi_notifications_path, '10', result_path])
    assert r.exit_code == 0

    gdf_result = gpd.read_file(result_path)
    assert gdf_result.crs == {'init': 'epsg:3301'}
    gdf_expected = gpd.read_file(expected_result_path)
    assert str(gdf_expected) == str(gdf_result)


@pytest.mark.vcr
def test_query_layer_empty_cli(tmpdir):
    result_path = str(tmpdir.join('result.geojson'))
    runner = CliRunner()
    r = runner.invoke(cli.cli, ['get_layer', aoi_empty_path, '10', result_path])
    assert r.exit_code == 0
    gdf_result = gpd.read_file(result_path)
    assert gdf_result.crs == {'init': 'epsg:3301'}
    assert gdf_result.shape == (0, 0)


@pytest.mark.vcr
def test_forest_stands_cli(tmpdir):
    result_path = str(tmpdir.join('result.geojson'))
    expected_result_path = join(fixtures_dir, 'result_stands.geojson')

    runner = CliRunner()
    r = runner.invoke(cli.cli, ['forest_stands', aoi_path, result_path, '--wait', '0.1'])
    assert r.exit_code == 0

    gdf_result = gpd.read_file(result_path)
    assert gdf_result.crs == {'init': 'epsg:3301'}
    gdf_expected = gpd.read_file(expected_result_path)
    assert str(gdf_expected) == str(gdf_result)


@pytest.mark.vcr
def test_forest_notifications_cli(tmpdir):
    result_path = str(tmpdir.join('result.geojson'))
    expected_result_path = join(fixtures_dir, 'result_notifications.geojson')

    runner = CliRunner()
    r = runner.invoke(cli.cli, ['forest_notifications', aoi_notifications_path, result_path,
                                '--wait', '0.1'])
    assert r.exit_code == 0

    gdf_result = gpd.read_file(result_path)
    assert gdf_result.crs == {'init': 'epsg:3301'}
    gdf_expected = gpd.read_file(expected_result_path)
    assert str(gdf_expected) == str(gdf_result)
