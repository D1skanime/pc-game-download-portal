"""Explicit provider-media discovery for the parent owned-media catalog.

This module deliberately consumes persisted provider media only.  It never
starts a scan and it never grants filesystem authority.
"""

from dataclasses import dataclass
from hashlib import sha256
from pathlib import PurePosixPath
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from models.rom import RomOwnedMediaRole, derive_owned_media_display_label

_MAX_PROVIDER_MEDIA = 500


@dataclass(frozen=True, slots=True)
class ProviderMediaCandidate:
    provider: str
    provider_media_id: str
    role: RomOwnedMediaRole
    url: str
    display_label: str


def normalize_provider_url(value: str) -> str:
    """Normalize an HTTPS URL to the stable identity used for refreshes."""
    parsed = urlsplit(value)
    if parsed.scheme.lower() != "https" or not parsed.netloc or parsed.username:
        raise ValueError("Provider media must use HTTPS")
    path = parsed.path or "/"
    query = urlencode(sorted(parse_qsl(parsed.query, keep_blank_values=True)))
    return urlunsplit(("https", parsed.netloc.lower(), path, query, ""))


def _candidate(
    provider: str, value: object, role: RomOwnedMediaRole
) -> ProviderMediaCandidate:
    if isinstance(value, dict):
        raw_url = value.get("url")
        native_id = value.get("id")
    else:
        raw_url = value
        native_id = None
    if not isinstance(raw_url, str):
        raise ValueError("Provider media URL is invalid")
    url = normalize_provider_url(raw_url)
    identity = (
        str(native_id)
        if native_id not in (None, "")
        else f"url-sha256:{sha256(url.encode()).hexdigest()}"
    )
    label = derive_owned_media_display_label(
        PurePosixPath(urlsplit(url).path).name or "provider-media"
    )
    return ProviderMediaCandidate(provider, identity[:450], role, url, label)


def discover_provider_media(
    provider: str, media: dict[str, object]
) -> list[ProviderMediaCandidate]:
    """Return the complete persisted screenshot/artwork inventory for refresh."""
    if not provider or len(provider) > 100:
        raise ValueError("Provider is invalid")
    candidates: list[ProviderMediaCandidate] = []
    for key, role in (
        ("url_screenshots", RomOwnedMediaRole.SCREENSHOT),
        ("url_artworks", RomOwnedMediaRole.ARTWORK),
    ):
        values = media.get(key, [])
        if not isinstance(values, list) or len(values) > _MAX_PROVIDER_MEDIA:
            raise ValueError("Provider media list is invalid or exceeds the limit")
        candidates.extend(_candidate(provider, value, role) for value in values)
    return candidates
