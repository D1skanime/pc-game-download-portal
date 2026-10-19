"""One locked view of every live owned-resource reference surface."""

from sqlalchemy import select

from models.assets import Screenshot
from models.collection import Collection
from models.rom import (
    Rom,
    RomComponentLocalMedia,
    RomComponentMetadata,
    RomComponentOwnedMedia,
    RomOwnedMedia,
    TrackMeta,
)

MAX_REFERENCE_ROWS = 50000


def locked_catalog_media_references(session):
    surfaces = [
        (
            Rom,
            [
                "path_cover_s",
                "path_cover_l",
                "path_manual",
                "path_screenshots",
                *(
                    key
                    for key in Rom.__table__.columns.keys()
                    if key.endswith("_metadata")
                ),
            ],
        ),
        (RomOwnedMedia, ["owned_path"]),
        (RomComponentOwnedMedia, ["owned_path"]),
        (RomComponentLocalMedia, ["owned_path"]),
        (RomComponentMetadata, list(RomComponentMetadata.__table__.columns.keys())),
        (TrackMeta, ["cover_path"]),
        (Collection, ["path_cover_s", "path_cover_l"]),
        (Screenshot, ["file_path", "file_name"]),
    ]
    values: list[object] = []
    for model, fields in surfaces:
        rows = (
            session.execute(
                select(*(getattr(model, field) for field in fields))
                .order_by(*model.__table__.primary_key.columns)
                .limit(MAX_REFERENCE_ROWS + 1)
                .with_for_update()
            )
            .mappings()
            .all()
        )
        if len(rows) > MAX_REFERENCE_ROWS:
            raise ValueError("collection_cleanup_reference_budget")
        values.extend(dict(row) for row in rows)
        if model is Screenshot:
            values.extend(
                str(row["file_path"]).rstrip("/") + "/" + str(row["file_name"])
                for row in rows
            )
    return values
