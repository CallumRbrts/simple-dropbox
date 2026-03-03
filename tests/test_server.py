import hashlib

def test_upload_creates_file(flask_client, dest_dir):
    data = b"hello world"
    resp = flask_client.put("/files/hello.txt", data=data)
    assert resp.status_code == 201
    assert (dest_dir / "hello.txt").read_bytes() == data


def test_upload_updates_existing_file(flask_client, dest_dir):
    flask_client.put("/files/doc.txt", data=b"v1")
    resp = flask_client.put("/files/doc.txt", data=b"v2")
    assert resp.status_code == 200
    assert (dest_dir / "doc.txt").read_bytes() == b"v2"


def test_upload_nested_path(flask_client, dest_dir):
    resp = flask_client.put("/files/a/b/c.txt", data=b"nested")
    assert resp.status_code == 201
    assert (dest_dir / "a" / "b" / "c.txt").exists()


def test_list_files_empty(flask_client):
    resp = flask_client.get("/files")
    assert resp.status_code == 200
    assert resp.get_json() == {}


def test_list_files_returns_checksums(flask_client):
    content = b"checksum test"
    flask_client.put("/files/check.txt", data=content)
    resp = flask_client.get("/files")
    body = resp.get_json()
    assert "check.txt" in body
    assert body["check.txt"] == hashlib.md5(content).hexdigest()


def test_delete_file(flask_client, dest_dir):
    flask_client.put("/files/to_delete.txt", data=b"bye")
    resp = flask_client.delete("/files/to_delete.txt")
    assert resp.status_code == 204
    assert not (dest_dir / "to_delete.txt").exists()


def test_delete_nonexistent_returns_404(flask_client):
    resp = flask_client.delete("/files/ghost.txt")
    assert resp.status_code == 404


def test_delete_prunes_empty_dirs(flask_client, dest_dir):
    flask_client.put("/files/sub/file.txt", data=b"x")
    flask_client.delete("/files/sub/file.txt")
    assert not (dest_dir / "sub").exists()


def test_upload_with_valid_checksum(flask_client):
    data = b"integrity check"
    md5 = hashlib.md5(data).hexdigest()
    resp = flask_client.put("/files/safe.txt", data=data, headers={"X-Checksum-MD5": md5})
    assert resp.status_code == 201


def test_upload_with_invalid_checksum_rejected(flask_client):
    resp = flask_client.put(
        "/files/bad.txt",
        data=b"real data",
        headers={"X-Checksum-MD5": "00000000000000000000000000000000"},
    )
    assert resp.status_code == 400


def test_path_traversal_rejected(flask_client):
    resp = flask_client.put("/files/../../etc/passwd", data=b"pwned")
    assert resp.status_code == 400