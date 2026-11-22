import pytest
from click.testing import CliRunner
from atlas.cli.main import cli
from atlas.runtime.container import DependencyContainer

@pytest.fixture
def runner():
    return CliRunner()

def test_status(runner, mocker):
    # Mock container and services
    mock_container = mocker.MagicMock(spec=DependencyContainer)
    mocker.patch("atlas.runtime.application.AtlasApplication.get_instance")
    # ... set up mocks for health, heartbeat, etc.
    result = runner.invoke(cli, ["status"])
    assert result.exit_code == 0
    assert "Runtime Status" in result.output

def test_stop(runner, mocker):
    mock_app = mocker.MagicMock()
    mocker.patch("atlas.runtime.application.AtlasApplication.get_instance", return_value=mock_app)
    result = runner.invoke(cli, ["stop"])
    assert result.exit_code == 0
    mock_app.shutdown.assert_called_once()

