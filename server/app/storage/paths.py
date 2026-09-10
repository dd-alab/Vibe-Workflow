import re
import unicodedata
from pathlib import Path

from app.domain.validation import (
    validate_relative_path as validate_domain_path,
)
from app.domain.validation import (
    validate_slug,
)


def slugify(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    ascii_value = normalized.encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-z0-9]+", "_", ascii_value.lower()).strip("_")
    return validate_slug(slug)


def validate_relative_path(value: str) -> str:
    return validate_domain_path(value)


def resolve_within(root: Path, relative_path: str | Path) -> Path:
    root = root.expanduser().resolve()
    candidate = (root / relative_path).resolve()
    if not candidate.is_relative_to(root):
        raise ValueError("path escapes the configured root")
    return candidate


def ensure_internal_directory(root: Path, name: str) -> Path:
    root = root.expanduser().resolve()
    directory = root / name
    is_junction = getattr(directory, "is_junction", lambda: False)
    if directory.is_symlink() or is_junction():
        raise ValueError(f"internal directory '{name}' cannot be a symlink or junction")

    directory.mkdir(parents=True, exist_ok=True)
    resolved = resolve_within(root, name)
    is_junction = getattr(directory, "is_junction", lambda: False)
    if directory.is_symlink() or is_junction() or not resolved.is_dir():
        raise ValueError(f"internal directory '{name}' cannot be a symlink or junction")
    return resolved
