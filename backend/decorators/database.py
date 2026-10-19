import functools
from contextlib import nullcontext

from fastapi import HTTPException, status
from sqlalchemy.exc import ProgrammingError

from handler.database.base_handler import sync_session
from handler.database.scan_write_fence import fence_bound_session
from logger.logger import log


def begin_session(func):
    # Operation transitions own their locks and must also work after revocation.
    operation_repository = func.__module__ == "handler.database.scan_operations_handler"

    def fence(session):
        return nullcontext() if operation_repository else fence_bound_session(session)

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        # Reuse a caller-provided session so the handler can join an existing unit of work
        if kwargs.get("session") is not None:
            with fence(kwargs["session"]):
                return func(*args, **kwargs)

        try:
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
