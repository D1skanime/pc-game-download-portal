"""Persisted operator intent shared by optimistic and locked media checks."""

from sqlalchemy import select

from models.rom import RomOwnedMedia, RomOwnedMediaOrigin


def is_suppressed(rows, provider, identity, role):
    """Only URL digests cross namespaces; native identities stay provider-qualified."""
    return any(
        row.operator_suppressed
        and row.role == role
        and row.provider_media_id == identity
        and (row.provider == provider or identity.startswith("url-sha256:"))
        for row in rows
        if row.origin == RomOwnedMediaOrigin.PROVIDER
    )


def suppressed_candidates(session, rom_id, candidates):
    """Batch the optimistic lookup; callers still recheck under the parent lock."""
    identities = {item.provider_media_id for item in candidates}
    if not identities:
        return set()
    rows = session.scalars(
        select(RomOwnedMedia).where(
            RomOwnedMedia.rom_id == rom_id,
            RomOwnedMedia.origin == RomOwnedMediaOrigin.PROVIDER,
            RomOwnedMedia.operator_suppressed.is_(True),
            RomOwnedMedia.provider_media_id.in_(identities),
        )
    ).all()
    return {
        (item.provider, item.provider_media_id, item.role)
        for item in candidates
        if is_suppressed(rows, item.provider, item.provider_media_id, item.role)
    }


def candidate_key(candidate):
    return candidate.provider, candidate.provider_media_id, candidate.role
