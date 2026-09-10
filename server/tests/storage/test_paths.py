from pathlib import Path

import pytest

from app.storage.paths import (
    ensure_internal_directory,
    resolve_within,
    validate_relative_path,
    validate_slug,
)


@pytest.mark.parametrize(
    "slug",
    [
        "../escape",
        "two/levels",
        "two\\levels",
        "UPPERCASE",
        " space ",
        "con",
        "com1",
    ],
)
def test_validate_slug_rejects_unsafe_values(slug) -> None:
    with pytest.raises(ValueError):
        validate_slug(slug)


def test_validate_slug_accepts_underscore_values() -> None:
    assert validate_slug("circus_portraits") == "circus_portraits"


@pytest.mark.parametrize(
    "relative_path",
    [
        "../secret.txt",
        "/absolute/file.png",
        "C:\\secret.png",
        "a\\b.png",
        "references/con.png",
        "references/image.png:stream",
        "references/trailing. ",
        ".",
        "references/control\u0001.png",
    ],
)
def test_validate_relative_path_rejects_unsafe_values(relative_path) -> None:
    with pytest.raises(ValueError):
        validate_relative_path(relative_path)


def test_resolve_within_rejects_paths_outside_root(tmp_path) -> None:
    with pytest.raises(ValueError):
        resolve_within(tmp_path, Path("..") / "outside")


def test_internal_directory_cannot_be_symlink(tmp_path) -> None:
    root = tmp_path / "root"
    outside = tmp_path / "outside"
    root.mkdir()
    outside.mkdir()

    try:
        (root / ".staging").symlink_to(outside, target_is_directory=True)
    except OSError:
        pytest.skip("directory symlinks require Windows developer mode")

    with pytest.raises(ValueError, match="symlink or junction"):
        ensure_internal_directory(root, ".staging")
