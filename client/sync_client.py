import hashlib
import logging
import time
from pathlib import Path

import requests
from watchdog.events import FileSystemEventHandler, FileSystemEvent
from watchdog.observers import Observer

CHUNK_SIZE = 65536

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


class SyncAPIClient:

    def __init__(self, base_url: str, timeout: int = 30):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._session = requests.Session()

    def list_files(self) -> dict:
        resp = self._session.get(f"{self.base_url}/files", timeout=self.timeout)
        resp.raise_for_status()
        return resp.json()

    def upload_file(self, relative_path: str, data: bytes) -> None:
        checksum = hashlib.md5(data).hexdigest()
        resp = self._session.put(
            f"{self.base_url}/files/{relative_path}",
            data=data,
            headers={"Content-Type": "application/octet-stream", "X-Checksum-MD5": checksum},
            timeout=self.timeout,
        )
        resp.raise_for_status()
        logger.info("Uploaded %s (%d bytes)", relative_path, len(data))

    def delete_file(self, relative_path: str) -> None:
        resp = self._session.delete(
            f"{self.base_url}/files/{relative_path}",
            timeout=self.timeout,
        )
        if resp.status_code == 404:
            logger.debug("Delete skipped (already absent): %s", relative_path)
            return
        resp.raise_for_status()
        logger.info("Deleted %s", relative_path)


def local_checksum(path: Path) -> str:
    h = hashlib.md5()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(CHUNK_SIZE), b""):
            h.update(chunk)
    return h.hexdigest()


def local_manifest(source: Path) -> dict:
    result = {}
    for p in source.rglob("*"):
        if p.is_file():
            rel = str(p.relative_to(source))
            result[rel] = local_checksum(p)
    return result


def initial_sync(source: Path, client: SyncAPIClient) -> None:
    logger.info("Starting initial sync")

    remote = client.list_files()
    local = local_manifest(source)

    for rel, local_cs in local.items():
        if remote.get(rel) != local_cs:
            data = (source / rel).read_bytes()
            client.upload_file(rel, data)

    for rel in remote:
        if rel not in local:
            client.delete_file(rel)

    logger.info("Initial sync complete.")


class SyncEventHandler(FileSystemEventHandler):

    def __init__(self, source: Path, client: SyncAPIClient):
        super().__init__()
        self.source = source
        self.client = client

    def _relative(self, abs_path: str) -> str | None:
        try:
            return str(Path(abs_path).relative_to(self.source))
        except ValueError:
            return None

    def on_created(self, event: FileSystemEvent) -> None:
        self._handle_file_change(event)

    def on_modified(self, event: FileSystemEvent) -> None:
        self._handle_file_change(event)

    def _handle_file_change(self, event: FileSystemEvent) -> None:
        if event.is_directory:
            return
        rel = self._relative(event.src_path)
        if rel:
            self._upload(rel)

    def on_deleted(self, event: FileSystemEvent) -> None:
        if event.is_directory:
            return
        rel = self._relative(event.src_path)
        if rel:
            try:
                self.client.delete_file(rel)
            except requests.RequestException as exc:
                logger.error("Failed to delete %s: %s", rel, exc)

    def on_moved(self, event: FileSystemEvent) -> None:
        if event.is_directory:
            return
        old_rel = self._relative(event.src_path)
        new_rel = self._relative(event.dest_path)
        if old_rel:
            try:
                self.client.delete_file(old_rel)
            except requests.RequestException as exc:
                logger.error("Failed to delete (on move) %s: %s", old_rel, exc)
        if new_rel:
            self._upload(new_rel)

    def _upload(self, relative_path: str) -> None:
        abs_path = self.source / relative_path
        try:
            data = abs_path.read_bytes()
        except OSError as exc:
            logger.warning("Could not read %s (may have been deleted): %s", relative_path, exc)
            return
        try:
            self.client.upload_file(relative_path, data)
        except requests.RequestException as exc:
            logger.error("Failed to upload %s: %s", relative_path, exc)


def run(source_dir: str, server_url: str, poll_interval: float = 1.0) -> None:
    source = Path(source_dir).resolve()
    if not source.is_dir():
        raise SystemExit(f"Source directory does not exist: {source}")

    client = SyncAPIClient(server_url)

    initial_sync(source, client)

    handler = SyncEventHandler(source, client)
    observer = Observer()
    observer.schedule(handler, str(source), recursive=True)
    observer.start()
    logger.info("Watching %s for changes (Ctrl+C to stop)...", source)

    try:
        while True:
            time.sleep(poll_interval)
    except KeyboardInterrupt:
        logger.info("Stopping...")
    finally:
        observer.stop()
        observer.join()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("source")
    parser.add_argument(
        "--server", default="http://127.0.0.1:5000"
    )
    args = parser.parse_args()

    run(args.source, args.server)