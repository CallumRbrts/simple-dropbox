from pathlib import Path
from unittest.mock import MagicMock

import requests

from client.sync_client import SyncEventHandler
from conftest import make_event


def test_on_created_uploads_file(source_dir, mock_api_client):
    (source_dir / "new.txt").write_bytes(b"created")
    handler = SyncEventHandler(source_dir, mock_api_client)
    handler.on_created(make_event(source_dir / "new.txt"))
    mock_api_client.upload_file.assert_called_once_with("new.txt", b"created")


def test_on_modified_uploads_file(source_dir, mock_api_client):
    (source_dir / "mod.txt").write_bytes(b"modified")
    handler = SyncEventHandler(source_dir, mock_api_client)
    handler.on_modified(make_event(source_dir / "mod.txt"))
    mock_api_client.upload_file.assert_called_once_with("mod.txt", b"modified")


def test_on_deleted_deletes_file(source_dir, mock_api_client):
    handler = SyncEventHandler(source_dir, mock_api_client)
    handler.on_deleted(make_event(source_dir / "gone.txt"))
    mock_api_client.delete_file.assert_called_once_with("gone.txt")


def test_ignores_directory_events(source_dir, mock_api_client):
    handler = SyncEventHandler(source_dir, mock_api_client)
    handler.on_created(make_event(source_dir / "subdir", is_directory=True))
    mock_api_client.upload_file.assert_not_called()


def test_on_moved_deletes_old_and_uploads_new(source_dir, mock_api_client):
    (source_dir / "dest.txt").write_bytes(b"moved content")
    handler = SyncEventHandler(source_dir, mock_api_client)
    evt = MagicMock()
    evt.src_path = str(source_dir / "src.txt")
    evt.dest_path = str(source_dir / "dest.txt")
    evt.is_directory = False
    handler.on_moved(evt)
    mock_api_client.delete_file.assert_called_once_with("src.txt")
    mock_api_client.upload_file.assert_called_once_with("dest.txt", b"moved content")


def test_on_deleted_logs_error_but_does_not_raise(source_dir, mock_api_client):
    mock_api_client.delete_file.side_effect = requests.RequestException("network error")
    handler = SyncEventHandler(source_dir, mock_api_client)
    handler.on_deleted(make_event(source_dir / "gone.txt"))


def test_on_moved_delete_failure_does_not_prevent_upload(source_dir, mock_api_client):
    mock_api_client.delete_file.side_effect = requests.RequestException("network error")
    (source_dir / "dest.txt").write_bytes(b"content")
    handler = SyncEventHandler(source_dir, mock_api_client)
    evt = MagicMock()
    evt.src_path = str(source_dir / "src.txt")
    evt.dest_path = str(source_dir / "dest.txt")
    evt.is_directory = False
    handler.on_moved(evt)
    mock_api_client.upload_file.assert_called_once_with("dest.txt", b"content")


def test_upload_does_not_raise_if_file_disappears(source_dir, mock_api_client):
    handler = SyncEventHandler(source_dir, mock_api_client)
    handler._upload("ghost.txt")
    mock_api_client.upload_file.assert_not_called()


def test_upload_network_error_does_not_raise(source_dir, mock_api_client):
    mock_api_client.upload_file.side_effect = requests.RequestException("network error")
    (source_dir / "file.txt").write_bytes(b"data")
    handler = SyncEventHandler(source_dir, mock_api_client)
    handler._upload("file.txt")


def test_relative_returns_relative_path(source_dir, mock_api_client):
    handler = SyncEventHandler(source_dir, mock_api_client)
    result = handler._relative(str(source_dir / "hello.txt"))
    assert result == "hello.txt"


def test_relative_returns_nested_path(source_dir, mock_api_client):
    handler = SyncEventHandler(source_dir, mock_api_client)
    result = handler._relative(str(source_dir / "a" / "b" / "c.txt"))
    assert result == str(Path("a") / "b" / "c.txt")


def test_relative_returns_none_if_path_outside_source(source_dir, mock_api_client):
    handler = SyncEventHandler(source_dir, mock_api_client)
    result = handler._relative("/some/completely/different/path.txt")
    assert result is None