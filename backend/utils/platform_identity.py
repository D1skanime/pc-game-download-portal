"""Shared canonical identity for the legacy PC folder alias."""


def legacy_platform_slug_for_filesystem_slug(
    filesystem_slug: str, known_platform_slugs: set[str]
) -> str:
    if filesystem_slug == "pc" and "pc" not in known_platform_slugs:
        return "win" if "win" in known_platform_slugs else filesystem_slug
    return filesystem_slug
