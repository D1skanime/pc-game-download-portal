"""Filesystem platform slug compatibility helpers."""

from collections.abc import Callable

CANONICAL_PC_FILESYSTEM_SLUG = "win"
LEGACY_PC_FILESYSTEM_SLUG = "pc"


def canonicalize_filesystem_slug(fs_slug: str) -> str:
    """Return the canonical filesystem slug for a platform input."""
    return (
        CANONICAL_PC_FILESYSTEM_SLUG
        if fs_slug == LEGACY_PC_FILESYSTEM_SLUG
        else fs_slug
    )


def resolve_filesystem_slug(fs_slug: str, exists: Callable[[str], bool]) -> str:
    """Prefer the canonical slug while retaining a read-only legacy fallback."""
    canonical = canonicalize_filesystem_slug(fs_slug)
    if (
        fs_slug in {CANONICAL_PC_FILESYSTEM_SLUG, LEGACY_PC_FILESYSTEM_SLUG}
        and not exists(CANONICAL_PC_FILESYSTEM_SLUG)
        and exists(LEGACY_PC_FILESYSTEM_SLUG)
    ):
        return LEGACY_PC_FILESYSTEM_SLUG
    return canonical
