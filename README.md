# File Sync

A lightweight, two-component Python application that mirrors a **source** directory to a **destination** directory over HTTP.

---

## Prerequisites

- Python 3.10 or newer (`python3 --version` to check)
- Two folders on your machine — one to use as source, one as destination

---

## Installation

Clone or download the project, then install dependencies from the project root:

```bash
pip install -r requirements.txt
```

---

## Usage

### 1. Start the server

Open a terminal and point the server at your destination folder:

```bash
python server/app.py /path/to/destination
```

---

### 2. Start the client

Open a second terminal and point the client at your source folder:

```bash
python client/sync_client.py /path/to/source
```

---

### 3. Try it out

With both running, test it by creating a file in the source folder:

```bash
echo "Hello, world!" > ~/Desktop/source/hello.txt
```

---

## Optional Flags

**Server:**

| Flag | Description |
|------|-------------|
| `--port 8080` | Listen on a different port (default: 5000) |
| `--host 0.0.0.0` | Accept connections from other machines on the network |

**Client:**

| Flag | Description |
|------|-------------|
| `--server http://host:port` | Point the client at a server on a different machine or port (default: `http://127.0.0.1:5000`) |

---

## Running Tests

```bash
pytest
```

---

## Design Notes

### Assumptions & trade-offs
- **One directional sync**: the application listens to events that happen on the source, any changes to destination won't be synced
- **No authentication**: a production system would use something like API keys
- **No chunked upload**: files are uploaded in a single request, in production systems large files would be streamed
- **Rename functionality**: the server treats renaming as two calls, a delete of the old path followed by an upload to the new path
- **MD5 over SHA-256**: while SHA-256 is safer, MD5 is faster, potentially need to switch to SHA-256 for production
- **No TLS**: traffic is plain HTTP, production should use HTTPS
- **Initialise Overhead**: currently the initial sync re-hashes everything on start-up, could implement a state to save the last known state of the source and only update the files that have changed 