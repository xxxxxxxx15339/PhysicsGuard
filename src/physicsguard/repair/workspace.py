"""Disposable source copies; originals are never written or restored over edits."""
from contextlib import contextmanager
import os
from pathlib import Path
from tempfile import TemporaryDirectory

from physicsguard.schemas.repairs import SourceSnapshot
from .sources import read_source, source_hash, REVIEWED_HASHES


@contextmanager
def source_workspace(snapshot: SourceSnapshot, proposed: str | None = None):
    if snapshot.source_file not in REVIEWED_HASHES:
        raise ValueError("workspace source must be an allowlisted basename")
    directory = TemporaryDirectory(prefix="physicsguard-repair-")
    root = Path(directory.name)
    active_error = None
    try:
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
        body_error = None
        try:
            yield root
        except BaseException as error:
            body_error = error
            raise
        finally:
            # Always inspect both copies, even if the body failed. Do not mask its error.
            problems = []
            for role, expected in (("original", snapshot.sha256), ("candidate", source_hash(proposed or snapshot.source_text))):
                try:
                    if source_hash(read_source(root / role, snapshot.source_file)) != expected:
                        problems.append(f"{role} source was modified")
                except (ValueError, OSError, UnicodeError) as error:
                    problems.append(f"{role} integrity unavailable: {error}")
            if problems:
                message = "Workspace integrity failure: " + "; ".join(problems)
                if body_error is not None:
                    body_error.add_note(message)
                else:
                    raise ValueError(message)
    except BaseException as error:
        active_error = error
        raise
    finally:
        try:
            directory.cleanup()
        except BaseException as error:
            if active_error is not None:
                active_error.add_note(f"Workspace cleanup failed: {type(error).__name__}")
            else:
                raise
