import functools
from contextlib import nullcontext

from fastapi import HTTPException, status
from sqlalchemy import event
from sqlalchemy.exc import ProgrammingError

from handler.database.base_handler import sync_session
from handler.database.scan_write_fence import fence_bound_session
from logger.logger import log


def owned_writer_domain():
    from handler.filesystem.owned_writer_domain import owned_writer_domain as domain

    return domain()


def begin_session(func):
    # Operation transitions own their locks and must also work after revocation.
    operation_repository = func.__module__ in {
        "handler.database.scan_operations_handler",
        "handler.database.scan_operation_lifecycle",
    }

    read_only = func.__name__.startswith(
        ("get_", "list_", "count_", "find_", "search_", "has_", "exists_")
    ) and not func.__name__.startswith("get_or_create")
    serialize = not operation_repository and not read_only

    def fence(session):
        return nullcontext() if operation_repository else fence_bound_session(session)

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        # Reuse a caller-provided session so the handler can join an existing unit of work
        if kwargs.get("session") is not None:
            session = kwargs["session"]
            if serialize and "_owned_writer_domain" not in session.info:
                domain = owned_writer_domain()
                domain.__enter__()
                session.info["_owned_writer_domain"] = domain
                if not session.in_transaction():
                    session.begin()
                if not session.info.get("_owned_writer_listener"):

                    def release_domain(current, transaction):
                        if transaction.parent is None:
                            held = current.info.pop("_owned_writer_domain", None)
                            if held is not None:
                                held.__exit__(None, None, None)

                    event.listen(session, "after_transaction_end", release_domain)
                    session.info["_owned_writer_listener"] = True
            with fence(session):
                return func(*args, **kwargs)

        try:
            with owned_writer_domain() if serialize else nullcontext():
                with sync_session.begin() as s:
                    kwargs["session"] = s
                    with fence(s):
                        return func(*args, **kwargs)
        except ProgrammingError as exc:
            log.critical(str(exc))
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)
            ) from exc

    return wrapper
