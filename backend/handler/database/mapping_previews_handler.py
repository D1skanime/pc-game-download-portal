from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import select
from sqlalchemy.orm import Session

from decorators.database import begin_session
from handler.database.base_handler import DBBaseHandler
from models.mapping_preview import MappingPreview

if TYPE_CHECKING:
    from handler.storage.preview import MappingPreviewResult


class DBMappingPreviewsHandler(DBBaseHandler):
    @begin_session
    def get(self, mapping_id: int, *, session: Session = None) -> MappingPreview | None:  # type: ignore
        return session.scalar(
            select(MappingPreview).where(MappingPreview.mapping_id == mapping_id)
        )

    @begin_session
    def mark_pending(self, mapping_id: int, revision: int, *, session: Session = None) -> MappingPreview:  # type: ignore
        preview = session.scalar(
            select(MappingPreview)
            .where(MappingPreview.mapping_id == mapping_id)
            .with_for_update()
        )
        if preview is None:
            preview = MappingPreview(
                mapping_id=mapping_id, state="pending", observed_revision=revision
            )
            session.add(preview)
        else:
            preview.state = "pending"
            preview.stale = preview.completed_at is not None
        session.flush()
        return preview

    @begin_session
    def save_result(self, mapping_id: int, revision: int, result: MappingPreviewResult, *, session: Session = None) -> MappingPreview:  # type: ignore
        preview = session.scalar(
            select(MappingPreview)
            .where(MappingPreview.mapping_id == mapping_id)
            .with_for_update()
        )
        if preview is None:
            preview = MappingPreview(mapping_id=mapping_id, observed_revision=revision)
            session.add(preview)
        preview.state, preview.observed_files = result.state, result.observed_files
        preview.observed_directories, preview.observed_bytes = (
            result.observed_directories,
            result.observed_bytes,
        )
        preview.lower_bound, preview.budget_reason, preview.problems = (
            result.lower_bound,
            result.budget_reason,
            result.problems,
        )
        preview.observed_revision, preview.stale = revision, False
        preview.completed_at = datetime.now(timezone.utc)
        session.flush()
        return preview
