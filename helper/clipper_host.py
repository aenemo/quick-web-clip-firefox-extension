"""Native messaging host for Quick Web Clip."""
import contextlib
import json
import logging
import logging.handlers
import struct
import sys
from pathlib import Path
from typing import BinaryIO, Callable

import compose

HOST_VERSION = "1.4.0"
PROTOCOL_VERSION = 1

log = logging.getLogger("qwc")


def setup_logging(path: Path) -> None:
    """Log to a rotating file (1 MB, 3 backups). Never log note bodies."""
    log.setLevel(logging.INFO)
    for h in list(log.handlers):
        log.removeHandler(h)
        h.close()
    handler = logging.handlers.RotatingFileHandler(
        path, maxBytes=1_000_000, backupCount=3, encoding="utf-8"
    )
    handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s")
    )
    log.addHandler(handler)


def read_message(stream: BinaryIO) -> dict | None:
    """Read one length-prefixed JSON message; None on EOF."""
    header = stream.read(4)
    if len(header) < 4:
        return None
    (length,) = struct.unpack("<I", header)
    body = stream.read(length)
    if len(body) < length:
        return None
    return json.loads(body.decode("utf-8"))


def write_message(stream: BinaryIO, obj: dict) -> None:
    body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
    stream.write(struct.pack("<I", len(body)) + body)
    stream.flush()


def _ping(msg: dict) -> dict:
    try:
        from yt_dlp.version import __version__ as yt_dlp_version
    except Exception:
        yt_dlp_version = None
    return {"ok": True, "version": HOST_VERSION, "ytDlp": yt_dlp_version}


ACTIONS: dict[str, Callable[[dict], dict]] = {"ping": _ping, "save": compose.save}


def _bad_request(message: str) -> dict:
    return {"ok": False, "error": "bad_request", "message": message}


def handle(msg: dict) -> dict:
    if not isinstance(msg, dict) or msg.get("v") != PROTOCOL_VERSION:
        return _bad_request("unsupported protocol version")
    action = msg.get("action")
    fn = ACTIONS.get(action) if isinstance(action, str) else None
    if fn is None:
        return _bad_request(f"unknown action: {action}")
    try:
        return fn(msg)
    except Exception as exc:
        log.exception("handler failed for action %s", action)
        return {"ok": False, "error": "internal", "message": str(exc)}


def serve(stdin: BinaryIO, stdout: BinaryIO) -> None:
    while True:
        msg = read_message(stdin)
        if msg is None:
            return
        with contextlib.redirect_stdout(sys.stderr):
            reply = handle(msg)
        write_message(stdout, reply)


def main() -> None:
    setup_logging(Path(__file__).resolve().parent / "clipper.log")
    serve(sys.stdin.buffer, sys.stdout.buffer)


if __name__ == "__main__":
    main()
