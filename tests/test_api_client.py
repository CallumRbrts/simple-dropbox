import hashlib

import pytest
import requests


def test_list_files_returns_parsed_response(api_client):
    expected = {"hello.txt": "abc123"}
    api_client._session.get.return_value.json.return_value = expected

    result = api_client.list_files()

    assert result == expected


def test_list_files_raises_on_error(api_client):
    api_client._session.get.return_value.raise_for_status.side_effect = requests.HTTPError()

    with pytest.raises(requests.HTTPError):
        api_client.list_files()


def test_upload_file_calls_put_with_correct_url(api_client):
    api_client.upload_file("hello.txt", b"data")

    assert "files/hello.txt" in api_client._session.put.call_args[0][0]


def test_upload_file_sends_correct_checksum_header(api_client):
    data = b"hello world"
    expected_checksum = hashlib.md5(data).hexdigest()

    api_client.upload_file("hello.txt", data)

    headers = api_client._session.put.call_args[1]["headers"]
    assert headers["X-Checksum-MD5"] == expected_checksum


def test_upload_file_raises_on_error(api_client):
    api_client._session.put.return_value.raise_for_status.side_effect = requests.HTTPError()

    with pytest.raises(requests.HTTPError):
        api_client.upload_file("hello.txt", b"data")


def test_delete_file_calls_delete_with_correct_url(api_client):
    api_client._session.delete.return_value.status_code = 204
    api_client.delete_file("hello.txt")

    assert "files/hello.txt" in api_client._session.delete.call_args[0][0]


def test_delete_file_404_is_silently_ignored(api_client):
    api_client._session.delete.return_value.status_code = 404

    api_client.delete_file("ghost.txt")

    api_client._session.delete.return_value.raise_for_status.assert_not_called()


def test_delete_file_raises_on_error(api_client):
    api_client._session.delete.return_value.status_code = 500
    api_client._session.delete.return_value.raise_for_status.side_effect = requests.HTTPError()

    with pytest.raises(requests.HTTPError):
        api_client.delete_file("hello.txt")