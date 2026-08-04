from pathlib import PureWindowsPath

from exceptions.storage_exceptions import InvalidRelativePathError


def normalize_relative_path(raw: str, *, allow_root: bool = False) -> str:
    """Validate and preserve a logical POSIX-style relative storage path."""
    if not isinstance(raw, str):
        raise InvalidRelativePathError

    if raw == "":
        if allow_root:
            return ""
        raise InvalidRelativePathError

    if any(ord(character) < 32 or ord(character) == 127 for character in raw):
        raise InvalidRelativePathError

    if "\\" in raw or raw.startswith("/"):
        raise InvalidRelativePathError

    if PureWindowsPath(raw).drive:
        raise InvalidRelativePathError

    segments = raw.split("/")
    if any(segment in {"", ".", ".."} for segment in segments):
        raise InvalidRelativePathError

    return raw
