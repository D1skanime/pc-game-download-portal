"""Stable auxiliary scan output replacement under the current SQL fence."""

import errno
from typing import cast

from sqlalchemy.exc import SQLAlchemyError

from handler.database.base_handler import sync_session
from handler.database.scan_write_fence import (
    checked_scan_write,
    current_scan_write_context,
)
from handler.filesystem.owned_content_proof import content_proof_scope
from handler.filesystem.owned_writer_domain import owned_writer_domain
from handler.filesystem.storage_access import (
    IndeterminateOwnedPublicationError,
    OwnedReplace,
    open_owned_access,
)
from handler.filesystem.storage_policy import StorageOperation


class ScanOutputPreparationError(OSError):
    """Ordinary local staging I/O failed before any stable replacement."""


def publish_scan_output(storage, relative_path, content):
    if not isinstance(content, bytes):
        raise TypeError("scan output requires serialized bytes")
    if current_scan_write_context() is None:
        raise RuntimeError("scan_context_required")
    with content_proof_scope(expected_bytes=len(content), expected_records=1):
        parent = relative_path.rpartition("/")[0]
        if parent:
            from handler.filesystem.scan_media_publication import ensure_directory

            with owned_writer_domain(), sync_session.begin() as session:
                with checked_scan_write(session):
                    ensure_directory(storage, parent)
        return _publish_prepared_output(storage, relative_path, content)


def _publish_prepared_output(storage, relative_path, content):
    published = False
    with open_owned_access(
        storage, StorageOperation.OVERWRITE, relative_path
    ) as destination:
        destination = cast(OwnedReplace, destination)
        prepared = None
        try:
            try:
                prepared = destination.prepare_binary_file()
                prepared.file.write(content)
                prepared.seal()
            except Exception as error:
                cause = error if isinstance(error, OSError) else error.__cause__
                if isinstance(cause, OSError) and cause.errno in {
                    errno.ENOSPC,
                    errno.EDQUOT,
                    errno.EIO,
                    errno.EMFILE,
                    errno.ENFILE,
                }:
                    raise ScanOutputPreparationError(
                        "scan_output_preparation_failed"
                    ) from None
                raise
            try:
                with owned_writer_domain(), sync_session.begin() as session:
                    with checked_scan_write(session):
                        prepared.publish(
                            final_authority_check=lambda: _assert_current(session)
                        )
                        published = True
            except SQLAlchemyError:
                if published:
                    raise IndeterminateOwnedPublicationError() from None
                raise
        finally:
            if prepared is not None:
                prepared.abort()


def export_scan_platform(platform_id, *, gamelist=False, pegasus=False):
    from handler.filesystem import storage_composition
    from handler.filesystem.storage_policy import OwnedStorageKind
    from utils.gamelist_exporter import GamelistExporter
    from utils.pegasus_exporter import PegasusExporter

    storage = storage_composition.owned[OwnedStorageKind.RESOURCES]
    if gamelist:
        content = GamelistExporter(local_export=True).export_platform_to_xml(
            platform_id, request=None
        )
        publish_scan_output(
            storage, f"gamelist_{platform_id}.xml", content.encode("utf-8")
        )
    if pegasus:
        content = PegasusExporter(local_export=True).export_platform_to_pegasus(
            platform_id, request=None
        )
        publish_scan_output(
            storage, f"metadata_pegasus_{platform_id}.txt", content.encode("utf-8")
        )


def _assert_current(session):
    with checked_scan_write(session):
        pass
