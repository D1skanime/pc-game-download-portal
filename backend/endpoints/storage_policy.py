from __future__ import annotations

from fastapi import HTTPException, status

from exceptions.storage_exceptions import StoragePolicyDenied
from handler.filesystem.storage_policy import (
    StorageDescriptor,
    StorageGrant,
    StorageOperation,
    StoragePolicy,
)


def authorize_api_storage_operation(
    operation: StorageOperation,
    storage: StorageDescriptor,
    *,
    caller_text: str | None = None,
) -> StorageGrant:
    """Translate one trusted storage policy decision for direct API callers."""
    del caller_text
    try:
        return StoragePolicy.authorize(operation, storage)
    except StoragePolicyDenied as denial:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": denial.code,
                "operation": denial.operation,
                "storage_class": denial.storage_class,
                "storage_id": denial.storage_id,
            },
        ) from denial
