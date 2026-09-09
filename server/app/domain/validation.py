import math
import re
from pathlib import PurePosixPath, PureWindowsPath
from typing import Any

SECRET_KEYS = {
    "api_key",
    "apikey",
    "authorization",
    "password",
    "private_key",
    "secret",
    "token",
}
SLUG_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
WINDOWS_RESERVED_NAMES = {
    "aux",
    "con",
    "nul",
    "prn",
    *(f"com{index}" for index in range(1, 10)),
    *(f"lpt{index}" for index in range(1, 10)),
}
WINDOWS_INVALID_CHARACTERS = set('<>:"|?*')
SENSITIVE_ASSIGNMENT_PATTERN = re.compile(
    r"(?i)\b(api[_ -]?key|authorization|password|secret|token)\b"
    r"\s*[:=]\s*([^\s,;]+)"
)
BEARER_PATTERN = re.compile(r"(?i)\bbearer\s+[^\s,;]+")


def validate_slug(value: str) -> str:
    if len(value) > 80 or not SLUG_PATTERN.fullmatch(value):
        raise ValueError("slug must contain lowercase letters, numbers, and hyphens")
    if value in WINDOWS_RESERVED_NAMES:
        raise ValueError("slug is reserved on Windows")
    return value


def validate_relative_path(value: str) -> str:
    if not value or "\\" in value:
        raise ValueError("path must be a non-empty POSIX relative path")

    posix_path = PurePosixPath(value)
    windows_path = PureWindowsPath(value)
    if not posix_path.parts:
        raise ValueError("path must identify a file")
    if posix_path.is_absolute() or windows_path.is_absolute():
        raise ValueError("absolute paths are not portable")
    if windows_path.drive:
        raise ValueError("drive-relative paths are not portable")
    if any(part in {"", ".", ".."} for part in posix_path.parts):
        raise ValueError("path traversal is not allowed")

    for part in posix_path.parts:
        if len(part) > 240:
            raise ValueError("path component is too long")
        if any(ord(character) < 32 for character in part):
            raise ValueError("path contains control characters")
        if part.rstrip(" .") != part:
            raise ValueError("path components cannot end with a dot or space")
        if any(character in WINDOWS_INVALID_CHARACTERS for character in part):
            raise ValueError("path contains characters forbidden on Windows")
        if part.split(".", 1)[0].lower() in WINDOWS_RESERVED_NAMES:
            raise ValueError("path contains a name reserved on Windows")

    return posix_path.as_posix()


def ensure_no_secrets(value: Any) -> Any:
    if isinstance(value, dict):
        for key, nested_value in value.items():
            normalized_key = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", str(key)).lower()
            normalized_key = re.sub(r"[^a-z0-9]+", "_", normalized_key).strip("_")
            key_parts = set(normalized_key.split("_"))
            if (
                normalized_key in SECRET_KEYS
                or key_parts & {"authorization", "password", "secret", "token"}
                or normalized_key.endswith("_api_key")
                or normalized_key.endswith("_password")
                or normalized_key.endswith("_secret")
                or normalized_key.endswith("_token")
            ):
                raise ValueError(f"secret field '{key}' cannot be serialized")
            ensure_no_secrets(nested_value)
    elif isinstance(value, (list, tuple)):
        for nested_value in value:
            ensure_no_secrets(nested_value)
    elif isinstance(value, float) and not math.isfinite(value):
        raise ValueError("non-finite numbers cannot be serialized")

    return value


def redact_secrets(value: str) -> str:
    redacted = SENSITIVE_ASSIGNMENT_PATTERN.sub(r"\1=[REDACTED]", value)
    return BEARER_PATTERN.sub("Bearer [REDACTED]", redacted)
