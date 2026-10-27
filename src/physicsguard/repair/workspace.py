"""Disposable source copies; originals are never written or restored over edits."""
from contextlib import contextmanager
import os
from pathlib import Path
from tempfile import TemporaryDirectory

from physicsguard.schemas.repairs import SourceSnapshot
from .sources import read_source, source_hash


@contextmanager
def source_workspace(snapshot: SourceSnapshot, proposed: str | None = None):
    with TemporaryDirectory(prefix="physicsguard-repair-") as directory:
        root = Path(directory)
        for role, text in (("original", snapshot.source_text), ("candidate", proposed or snapshot.source_text)):
            folder = root / role
            folder.mkdir(mode=0o700)
            temporary = folder / ".source.pending"
            with temporary.open("x", encoding="utf-8") as stream:
                stream.write(text)
                stream.flush()
                os.fsync(stream.fileno())
            target = folder / snapshot.source_file
            os.replace(temporary, target)
            target.chmod(0o400)
        yield root
        # These hashes detect accidental tampering; permissions are not an OS sandbox.
        if source_hash(read_source(root / "original", snapshot.source_file)) != snapshot.sha256:
            raise ValueError("disposable original source was modified")
        if source_hash(read_source(root / "candidate", snapshot.source_file)) != source_hash(proposed or snapshot.source_text):
            raise ValueError("candidate source was modified during execution")
