import hashlib
import logging
from pathlib import Path

from flask import Flask, request, jsonify, abort

CHUNK_SIZE = 65536

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def create_app(destination_dir: str) -> Flask:

    destination = Path(destination_dir).resolve()
    if not destination.exists():
        destination.mkdir(parents=True)
        logger.info("Created destination directory: %s", destination)

    app = Flask(__name__)
    app.config["DESTINATION"] = destination

    @app.route("/files", methods=["GET"])
    def list_files():
        result = {}
        for p in destination.rglob("*"):
            if p.is_file():
                rel = _relative(p)
                result[rel] = _file_checksum(p)
        return jsonify(result)

    @app.route("/files/<path:relative_path>", methods=["PUT"])
    def upload_file(relative_path: str):
        full = _safe_path(relative_path)
        full.parent.mkdir(parents=True, exist_ok=True)

        data = request.get_data()

        expected_checksum = request.headers.get("X-Checksum-MD5")
        if expected_checksum:
            actual = hashlib.md5(data).hexdigest()
            if actual != expected_checksum:
                abort(400, f"Checksum mismatch: expected {expected_checksum}, got {actual}")

        existed = full.exists()
        full.write_bytes(data)

        logger.info("%s %s (%d bytes)", "Updated" if existed else "Created", relative_path, len(data))
        status = 200 if existed else 201
        return jsonify({"path": relative_path, "size": len(data)}), status

    @app.route("/files/<path:relative_path>", methods=["DELETE"])
    def delete_file(relative_path: str):
        full = _safe_path(relative_path)
        if not full.exists():
            abort(404, f"File not found: {relative_path}")

        full.unlink()
        logger.info("Deleted %s", relative_path)
        _prune_empty_dirs(full.parent)
        return "", 204


    def _safe_path(relative: str) -> Path:
        relative = relative.replace("\\", "/").lstrip("/")
        full = (destination / relative).resolve()
        if not str(full).startswith(str(destination)):
            abort(400, "Path traversal detected")
        return full

    def _file_checksum(path: Path) -> str:
        h = hashlib.md5()
        with path.open("rb") as f:
            for chunk in iter(lambda: f.read(CHUNK_SIZE), b""):
                h.update(chunk)
        return h.hexdigest()

    def _relative(path: Path) -> str:
        return str(path.relative_to(destination))

    def _prune_empty_dirs(directory: Path) -> None:
        while directory != destination and directory.exists() and not any(directory.iterdir()):
            directory.rmdir()
            logger.debug("Removed empty directory: %s", directory)
            directory = directory.parent

    return app


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("destination")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=5000)
    args = parser.parse_args()

    application = create_app(args.destination)
    logger.info("Starting server on %s:%d, destination=%s", args.host, args.port, args.destination)
    application.run(host=args.host, port=args.port)