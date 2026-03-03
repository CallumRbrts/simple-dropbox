from pathlib import Path
from unittest.mock import MagicMock

import pytest

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from server.app import create_app
from client.sync_client import SyncAPIClient


@pytest.fixture()
def dest_dir(tmp_path):
    return tmp_path / "destination"


@pytest.fixture()
def source_dir(tmp_path):
    d = tmp_path / "source"
    d.mkdir()
    return d


@pytest.fixture()
def flask_client(dest_dir):
    app = create_app(str(dest_dir))
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


@pytest.fixture()
def mock_api_client():
    client = MagicMock(spec=SyncAPIClient)
    client.list_files.return_value = {}
    return client


@pytest.fixture()
def api_client():
    c = SyncAPIClient("http://127.0.0.1:5000")
    c._session = MagicMock()
    return c


def make_event(path, is_directory=False):
    evt = MagicMock()
    evt.src_path = str(path)
    evt.is_directory = is_directory
    return evt