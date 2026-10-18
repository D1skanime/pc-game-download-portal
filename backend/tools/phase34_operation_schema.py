"""Exercise actual operation tables on each independently provisioned SQL dialect."""

from secrets import token_hex

from sqlalchemy import func, select
from sqlalchemy.exc import DatabaseError, IntegrityError
from sqlalchemy.orm import Session

from handler.database import db_user_handler  # noqa: F401, register catalog mappers
from models.platform import Platform
from models.scan_operation import ScanExecutionSlot, ScanOperation, ScanOperationItem
from models.storage import PlatformStorageMapping, StorageRoot
from models.user import Role, User


def check_operations(engine):
    with Session(engine) as session, session.begin():
        slot = session.scalar(select(ScanExecutionSlot).with_for_update())
        assert slot.id == 1 and slot.active_operation_id is None and slot.version == 0
        user = User(
            username="schema-operation", hashed_password=token_hex(32), role=Role.ADMIN
        )
        platform = Platform(name="Schema", slug="schema", fs_slug="schema")
        root = StorageRoot(name="Synthetic", container_path="/phase34/owned/library")
        session.add_all([user, platform, root])
        session.flush()
        mapping = PlatformStorageMapping(
            platform_id=platform.id, storage_root_id=root.id, relative_path="PC"
        )
        session.add(mapping)
        session.flush()

        def operation(identity="schema-op", **changes):
            data = dict(
                id=identity,
                actor_id=user.id,
                request_key="schema-key",
                payload_digest="a" * 64,
                command={"commands": []},
                rq_job_id=identity,
            )
            return ScanOperation(**(data | changes))

        row = operation()
        session.add(row)
        session.flush()
        slot.active_operation_id = row.id
        session.flush()
        for duplicate in (
            operation("duplicate"),
            operation("missing-user", actor_id=-999, request_key="other"),
            operation("bad-state", state="disconnected", request_key="state"),
            operation("bad-version", version=0, request_key="version"),
            ScanExecutionSlot(id=2),
        ):
            try:
                with session.begin_nested():
                    session.add(duplicate)
                    session.flush()
            except DatabaseError as error:
                if not isinstance(error, IntegrityError) and getattr(
                    error.orig, "errno", None
                ) not in {3819, 4025}:
                    raise
            else:
                raise AssertionError("missing operation constraint")
        item = ScanOperationItem(
            operation_id=row.id,
            target_key="schema-item",
            mapping_id=mapping.id,
            expected_revision=1,
            relative_path="game",
            provider="igdb",
            outcome="indexed",
            attempt_id="schema-attempt",
        )
        session.add(item)
        session.flush()
        try:
            with session.begin_nested():
                session.add(
                    ScanOperationItem(
                        operation_id="missing",
                        target_key="missing",
                        mapping_id=mapping.id,
                        expected_revision=1,
                        relative_path="game",
                        provider="igdb",
                        outcome="indexed",
                        attempt_id="schema-attempt",
                    )
                )
                session.flush()
        except IntegrityError:
            pass
        else:
            raise AssertionError("missing item operation FK")
        row.version += 1
        row.state = "queued"
        session.flush()
        assert (
            row.version == 2
            and session.scalar(select(func.count()).select_from(ScanOperationItem)) == 1
        )
        slot.active_operation_id = None
        slot.version = 0
        session.flush()
        session.delete(row)
        session.flush()
        assert session.scalar(select(func.count()).select_from(ScanOperationItem)) == 0
        session.delete(mapping)
        session.flush()
        for obj in (platform, root, user):
            session.delete(obj)
    print(
        "PASS actual operation CRUD, uniqueness, state/version checks, singleton and foreign keys:",
        engine.dialect.name,
    )
