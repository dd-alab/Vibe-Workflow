from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from threading import Lock, RLock

import portalocker

from app.storage.paths import ensure_internal_directory

_registry_guard = Lock()
_project_locks: dict[Path, RLock] = {}


def _get_project_lock(project_directory: Path) -> RLock:
    key = project_directory.resolve()
    with _registry_guard:
        return _project_locks.setdefault(key, RLock())


@contextmanager
def project_lock(project_directory: Path) -> Iterator[None]:
    lock = _get_project_lock(project_directory)
    with lock:
        locks_directory = ensure_internal_directory(project_directory.parent, ".locks")
        lock_file = locks_directory / f"{project_directory.name}.lock"
        with portalocker.Lock(lock_file, mode="a", timeout=30):
            yield
