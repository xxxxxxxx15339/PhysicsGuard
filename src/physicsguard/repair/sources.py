"""Reviewed fixture identities and immutable snapshots, without fault labels."""
from hashlib import sha256
import os
from pathlib import Path
import stat

from physicsguard.schemas.repairs import SourceSnapshot

REVIEWED_HASHES = {
    "solver_01.py": "0d7d53c3e9a545ef408d67995aec5b235b4885d0c6f54aee2fedeb6768a0ddcb",
    "solver_02.py": "29b8a1ed63aae6083a5274fc7da85c626c72af0fd482be65bebf2ea1a530056d",
    "solver_03.py": "1665e562ec568cadc8cbf183eafc641caba198fe8ab0bc3fed3d1a9439077ac8",
    "solver_04.py": "490fe581a243b953fb0de9771dbe7d7d3bc3a1ca6e9d83f1a1288a0cf918c87c",
}
MAX_SOURCE_BYTES = 20_000


def source_hash(text: str) -> str:
    return sha256(text.encode("utf-8")).hexdigest()


def checked_path(root: Path, name: str) -> Path:
    if name not in REVIEWED_HASHES:
        raise ValueError("source file is not an allowlisted fixture basename")
    root = Path(root).absolute()
    path = root / name
    if any(p.is_symlink() for p in (path, *path.parents)):
        raise ValueError("symlinks are not permitted")
    if not root.is_dir() or not path.is_file():
        raise ValueError("expected a regular fixture file in its source directory")
    return path


def read_source(root: Path, name: str) -> str:
    path = checked_path(root, name)
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(descriptor, "rb") as stream:
        info = os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_size > MAX_SOURCE_BYTES:
            raise ValueError("source must be a bounded regular file without hard links")
        data = stream.read(MAX_SOURCE_BYTES + 1)
    if len(data) > MAX_SOURCE_BYTES:
        raise ValueError("source size limit exceeded")
    return data.decode("utf-8")


class SourceStore:
    """Host-owned allowlist of exactly four reviewed originals, not an upload API."""
    def __init__(self, root: Path):
        self.root = Path(root).absolute()

    def inspect(self, name: str) -> SourceSnapshot:
        text = read_source(self.root, name)
        digest = source_hash(text)
        if digest != REVIEWED_HASHES[name]:
            raise ValueError("source hash does not match a reviewed original")
        return SourceSnapshot(name, digest, text)

    def unchanged(self, snapshot: SourceSnapshot) -> bool:
        try:
            return self.inspect(snapshot.source_file) == snapshot
        except (ValueError, OSError, UnicodeError):
            return False


def default_source_store() -> SourceStore:
    return SourceStore(Path(__file__).resolve().parents[3] / "benchmarks" / "source_fixtures")
