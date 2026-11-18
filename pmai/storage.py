"""Project persistence.

Two on-disk formats are supported:

* ``.pmproj`` — human-readable JSON, ideal for git and manual inspection
* ``.bin``    — gzip-compressed JSON with a PMAI magic header

Both formats are completely offline and require no database server.
"""

from __future__ import annotations

import gzip
import json
import os
import tempfile
import zlib
from pathlib import Path

from .models import Project, utc_now

BIN_MAGIC = b"PMAI-BIN\x01\n"
PROJECT_FILTERS = [
    ("PMAI project", "*.pmproj"),
    ("PMAI binary project", "*.bin"),
    ("All files", "*.*"),
]


class ProjectFileError(Exception):
    """Raised when a project file cannot be saved or loaded."""


def is_binary_path(path: str | Path) -> bool:
    return Path(path).suffix.lower() in {".bin", ".pmb"}


def encode_project(project: Project, *, binary: bool) -> bytes:
    """Serialize a project to bytes.

    The project's ``updated_at`` timestamp is refreshed before encoding.
    """
    project.updated_at = utc_now()
    try:
        data = json.dumps(
            project.to_dict(),
            ensure_ascii=False,
            indent=2,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise ProjectFileError(f"Could not serialize the project: {exc}") from exc
    if binary:
        return BIN_MAGIC + gzip.compress(data, compresslevel=9)
    return data + b"\n"


def decode_project(raw: bytes) -> Project:
    """Deserialize a project from either supported on-disk format."""
    try:
        if raw.startswith(BIN_MAGIC):
            raw = gzip.decompress(raw[len(BIN_MAGIC):])
        elif raw.startswith(b"\x1f\x8b"):
            raw = gzip.decompress(raw)
        try:
            text = raw.decode("utf-8-sig")
        except UnicodeDecodeError as exc:
            raise ProjectFileError(
                "The file is not a valid PMAI project (not UTF-8 text)."
            ) from exc
        data = json.loads(text)
    except ProjectFileError:
        raise
    except (OSError, EOFError, gzip.BadGzipFile, zlib.error) as exc:
        raise ProjectFileError(f"The project file is corrupted: {exc}") from exc
    except (json.JSONDecodeError, UnicodeError) as exc:
        raise ProjectFileError(f"The project file is not valid JSON: {exc}") from exc

    try:
        return Project.from_dict(data)
    except ValueError as exc:
        raise ProjectFileError(str(exc)) from exc


def save_project(project: Project, path: str | Path) -> Path:
    """Atomically save a project. Returns the resolved path."""
    target = Path(path).expanduser()
    if not target.suffix:
        target = target.with_suffix(".pmproj")
    binary = is_binary_path(target)
    payload = encode_project(project, binary=binary)

    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp_name = tempfile.mkstemp(
            prefix=f".{target.name}.",
            suffix=".tmp",
            dir=str(target.parent),
        )
        try:
            with os.fdopen(fd, "wb") as handle:
                handle.write(payload)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(tmp_name, target)
        finally:
            if os.path.exists(tmp_name):
                try:
                    os.unlink(tmp_name)
                except OSError:
                    pass
    except OSError as exc:
        raise ProjectFileError(f"Could not save the project: {exc}") from exc
    return target


def load_project(path: str | Path) -> Project:
    source = Path(path).expanduser()
    try:
        raw = source.read_bytes()
    except OSError as exc:
        raise ProjectFileError(f"Could not open the project: {exc}") from exc
    return decode_project(raw)
