from os.path import abspath, dirname, join

import pytest
from click.testing import CliRunner

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

    with open(result_path, encoding='utf8') as f:
        result = f.read()

    with open(expected_result_path, encoding='utf8') as f:
        expected = f.read()

    assert result == expected


@pytest.mark.vcr
def test_query_layer(tmpdir):
    runner = CliRunner()
    result_path = str(tmpdir.join('result.geojson'))
    expected_result_path = join(fixtures_dir, 'result_layer10.geojson')
    runner.invoke(cli.cli, ['query_layer', aoi_path, '10', result_path])

    with open(result_path, encoding='utf8') as f:
        result = f.read()

    with open(expected_result_path, encoding='utf8') as f:
        expected = f.read()

    assert result == expected
