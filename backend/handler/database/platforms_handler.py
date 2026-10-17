import functools
from collections.abc import Sequence
from datetime import datetime

from sqlalchemy import delete, select, update
from sqlalchemy.orm import Query, QueryableAttribute, Session, load_only, selectinload

from decorators.database import begin_session
from models.platform import Platform
from models.rom import Rom
from utils.platform_slugs import canonicalize_filesystem_slug

from .base_handler import DBBaseHandler


def with_firmware(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        kwargs["query"] = select(Platform).options(
            selectinload(Platform.firmware),
        )
        return func(*args, **kwargs)

    return wrapper


class DBPlatformsHandler(DBBaseHandler):
    @begin_session
    @with_firmware
    def add_platform(
        self,
        platform: Platform,
        query: Query = None,  # type: ignore
        session: Session = None,  # type: ignore
    ) -> Platform:
        platform = session.merge(platform)
        session.flush()

        return session.scalar(query.filter_by(id=platform.id).limit(1))

    @begin_session
    def update_platform(
        self,
        id: int,
        data: dict,
        session: Session = None,  # type: ignore
    ) -> Platform:
        session.execute(
            update(Platform)
            .where(Platform.id == id)
            .values(**data)
            .execution_options(synchronize_session="evaluate")
        )
        return session.query(Platform).filter_by(id=id).one()

    @begin_session
    @with_firmware
    def get_platform(
        self,
        id: int,
        query: Query = None,  # type: ignore
        session: Session = None,  # type: ignore
    ) -> Platform | None:
        return session.scalar(query.filter_by(id=id).limit(1))

    @begin_session
    @with_firmware
    def get_platforms(
        self,
        updated_after: datetime | None = None,
        only_fields: Sequence[QueryableAttribute] | None = None,
        hidden_platform_ids: Sequence[int] | None = None,
        query: Query = None,  # type: ignore
        session: Session = None,  # type: ignore
    ) -> Sequence[Platform]:
        if updated_after:
            query = query.filter(Platform.updated_at > updated_after)

        # Admin-driven visibility (opt-out): exclude platforms hidden from the
        # caller. Empty/None (e.g. admins) skips filtering.
        if hidden_platform_ids:
            query = query.filter(Platform.id.not_in(hidden_platform_ids))

        if only_fields:
            query = query.options(load_only(*only_fields))

        return session.scalars(query.order_by(Platform.name.asc())).unique().all()

    @begin_session
    @with_firmware
    def get_platform_by_fs_slug(
        self,
        fs_slug: str,
        query: Query = None,  # type: ignore
        session: Session = None,  # type: ignore
    ) -> Platform | None:
        canonical_slug = canonicalize_filesystem_slug(fs_slug)
        platforms = session.scalars(query).unique().all()
        return next(
            (
                platform
                for platform in sorted(
                    platforms,
                    key=lambda platform: platform.fs_slug != canonical_slug,
                )
                if canonicalize_filesystem_slug(platform.fs_slug) == canonical_slug
            ),
            None,
        )

    @begin_session
    @with_firmware
    def get_platform_by_slug(
        self,
        slug: str,
        query: Query = None,  # type: ignore
        session: Session = None,  # type: ignore
    ) -> Platform | None:
        return session.scalar(query.filter_by(slug=slug).limit(1))

    @begin_session
    def delete_platform(
        self,
        id: int,
        session: Session = None,  # type: ignore
    ) -> None:
        # Remove all roms from that platforms first
        session.execute(
            delete(Rom)
            .where(Rom.platform_id == id)
            .execution_options(synchronize_session="evaluate")
        )

        session.execute(
            delete(Platform)
            .where(Platform.id == id)
            .execution_options(synchronize_session="evaluate")
        )

    @begin_session
    def mark_missing_platforms(
        self,
        fs_platforms_to_keep: list[str],
        platform_ids: Sequence[int] | None = None,
        query: Query = None,  # type: ignore
        session: Session = None,  # type: ignore
    ) -> Sequence[Platform]:
        keep_slugs = {
            canonicalize_filesystem_slug(fs_slug) for fs_slug in fs_platforms_to_keep
        }
        scope = select(Platform).order_by(Platform.name.asc())
        if platform_ids is not None:
            scope = scope.where(Platform.id.in_(platform_ids))

        scoped_platforms = session.scalars(scope).unique().all()
        missing_platforms = [
            platform
            for platform in scoped_platforms
            if platform.slug is None
            or canonicalize_filesystem_slug(platform.fs_slug) not in keep_slugs
        ]
        missing_platform_ids = [platform.id for platform in missing_platforms]
        if missing_platform_ids:
            session.execute(
                update(Platform)
                .where(Platform.id.in_(missing_platform_ids))
                .values(**{"missing_from_fs": True})
                .execution_options(synchronize_session="fetch")
            )
            session.execute(
                update(Rom)
                .where(Rom.platform_id.in_(missing_platform_ids))  # type: ignore[attr-defined]
                .values(**{"missing_from_fs": True})
                .execution_options(synchronize_session="fetch")
            )
        return missing_platforms
