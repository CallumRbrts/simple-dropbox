import hashlib

from client.sync_client import initial_sync


def test_initial_sync_uploads_new_files(source_dir, mock_api_client):
    (source_dir / "new.txt").write_bytes(b"new content")
    mock_api_client.list_files.return_value = {}

    initial_sync(source_dir, mock_api_client)

    mock_api_client.upload_file.assert_called_once_with("new.txt", b"new content")


def test_initial_sync_skips_unchanged_files(source_dir, mock_api_client):
    content = b"unchanged"
    (source_dir / "same.txt").write_bytes(content)
    mock_api_client.list_files.return_value = {"same.txt": hashlib.md5(content).hexdigest()}

    initial_sync(source_dir, mock_api_client)

    mock_api_client.upload_file.assert_not_called()


def test_initial_sync_uploads_changed_files(source_dir, mock_api_client):
    content = b"new version"
    (source_dir / "changed.txt").write_bytes(content)
    mock_api_client.list_files.return_value = {"changed.txt": "old_checksum"}

    initial_sync(source_dir, mock_api_client)

    mock_api_client.upload_file.assert_called_once_with("changed.txt", content)


def test_initial_sync_deletes_remote_orphans(source_dir, mock_api_client):
    mock_api_client.list_files.return_value = {"orphan.txt": "abc"}

    initial_sync(source_dir, mock_api_client)

    mock_api_client.delete_file.assert_called_once_with("orphan.txt")