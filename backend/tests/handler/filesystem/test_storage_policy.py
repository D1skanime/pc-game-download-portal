import builtins
import importlib
import os
import shutil
import tempfile
from pathlib import Path

import pytest

from exceptions.storage_exceptions import StoragePolicyDenied
from handler.filesystem.storage_composition import build_storage_composition
from handler.filesystem.storage_policy import (
    EXTERNAL_READ_OPERATIONS,
    ExternalStorageDescriptor,
    OwnedStorageDescriptor,
    OwnedStorageKind,
    StorageOperation,
    StoragePolicy,
    create_owned_descriptor,
    validate_disjoint_storage_roots,
)
from models.storage import EXTERNAL_READ_ONLY_MODE, StorageRoot

READS = {
    StorageOperation.RESOLVE,
    StorageOperation.LIST,
    StorageOperation.STAT,
    StorageOperation.READ,
    StorageOperation.SCAN,
    StorageOperation.HASH,
    StorageOperation.STREAM,
    StorageOperation.DOWNLOAD,
}
MUTATIONS = set(StorageOperation) - READS


@pytest.fixture(scope="session", autouse=True)
def setup_database() -> None:
    """The policy unit suite is deliberately filesystem and database free."""


@pytest.fixture(autouse=True)
def clear_database() -> None:
    """Override the shared database cleanup for this pure policy suite."""


def _root(path: str = "/external/archive") -> StorageRoot:
    root = StorageRoot(
        name="Archive", container_path=path, mode=EXTERNAL_READ_ONLY_MODE, active=True
    )
    root.id = 17
    return root


@pytest.fixture
def external() -> ExternalStorageDescriptor:
    return build_storage_composition().legacy_external


@pytest.mark.parametrize("operation", sorted(READS, key=str))
def test_external_closed_allowlist_returns_operation_bound_grant(external, operation):
    grant = StoragePolicy.authorize(operation, external)
    assert grant.operation is operation and grant.storage is external
    assert not hasattr(grant, "path")


def test_external_allowlist_is_exact():
    assert EXTERNAL_READ_OPERATIONS == READS


@pytest.mark.parametrize("operation", sorted(MUTATIONS, key=str))
def test_every_external_mutation_denies(external, operation):
    with pytest.raises(StoragePolicyDenied):
        StoragePolicy.authorize(operation, external)


@pytest.mark.parametrize("operation", ["READ", "read", "future", object()])
def test_unknown_operations_fail_closed(external, operation):
    with pytest.raises(StoragePolicyDenied) as error:
        StoragePolicy.authorize(operation, external)
    assert error.value.operation == "unknown"


@pytest.mark.parametrize("operation", sorted(MUTATIONS, key=str))
def test_denial_precedes_all_filesystem_access(monkeypatch, external, operation):
    def forbidden(*args, **kwargs):
        raise AssertionError("filesystem access before denial")

    for owner, name in (
        (Path, "stat"),
        (Path, "lstat"),
        (Path, "open"),
        (Path, "iterdir"),
        (Path, "mkdir"),
        (Path, "unlink"),
        (Path, "rename"),
        (Path, "replace"),
        (os, "stat"),
        (os, "scandir"),
        (shutil, "copy"),
        (shutil, "copy2"),
        (shutil, "copytree"),
        (shutil, "move"),
        (tempfile, "NamedTemporaryFile"),
        (tempfile, "TemporaryFile"),
        (builtins, "open"),
    ):
        monkeypatch.setattr(owner, name, forbidden)
    with pytest.raises(StoragePolicyDenied):
        StoragePolicy.authorize(operation, external)


def test_source_and_destination_require_independent_grants(external):
    source = StoragePolicy.authorize(StorageOperation.READ, external)
    owned = create_owned_descriptor(OwnedStorageKind.TEMP, "patch-output")
    destination = StoragePolicy.authorize(StorageOperation.WRITE, owned)
    assert source.operation is StorageOperation.READ
    assert destination.operation is StorageOperation.WRITE
    assert source.storage is not destination.storage
    with pytest.raises(StoragePolicyDenied):
        StoragePolicy.authorize(StorageOperation.WRITE, external)


@pytest.mark.parametrize("kind", list(OwnedStorageKind))
@pytest.mark.parametrize("operation", list(StorageOperation))
def test_explicit_owned_kinds_accept_closed_operations(kind, operation):
    owned = create_owned_descriptor(kind, f"owned-{kind.value}")
    assert StoragePolicy.authorize(operation, owned).operation is operation


def test_descriptor_constructors_are_not_publicly_forgeable():
    with pytest.raises(TypeError):
        ExternalStorageDescriptor()
    with pytest.raises(TypeError):
        OwnedStorageDescriptor()


@pytest.mark.parametrize(
    "text",
    [
        "/external/archive",
        "external/archive",
        "/external/archive/../archive",
        "../../archive",
    ],
)
def test_caller_path_text_cannot_reclassify(external, text):
    assert text not in (external.root_id, external.mapping_id, external.storage_class)
    with pytest.raises((TypeError, ValueError)):
        create_owned_descriptor(text, "forged")


def test_external_descriptor_factory_is_not_public_runtime_surface():
    policy = importlib.import_module("handler.filesystem.storage_policy")
    assert not hasattr(policy, "create_external_descriptor")


def test_unsaved_storage_root_cannot_create_external_authority():
    policy = importlib.import_module("handler.filesystem.storage_policy")
    forged = _root("/caller/selected/archive")
    forged.id = 991
    assert getattr(policy, "create_external_descriptor", None) is None


def test_external_descriptor_contains_only_trusted_identity(external):
    descriptor = external
    assert (descriptor.root_id, descriptor.mapping_id) == (0, None)
    assert not hasattr(descriptor, "path")
    assert not hasattr(descriptor, "container_path")


@pytest.mark.parametrize(
    ("external_root", "owned_root"),
    [
        ("/romm/library", "/romm/library"),
        ("/romm/library", "/romm/library/cache"),
        ("/romm/library/nested", "/romm/library"),
    ],
)
def test_owned_and_external_roots_must_be_disjoint(external_root, owned_root):
    with pytest.raises(ValueError, match="disjoint"):
        validate_disjoint_storage_roots([external_root], [owned_root])


def test_disjoint_sibling_roots_are_accepted():
    validate_disjoint_storage_roots(
        ["/romm/library", "/mnt/archive"], ["/romm/resources", "/romm/assets"]
    )


def test_policy_denial_is_bounded_and_path_free(external):
    with pytest.raises(StoragePolicyDenied) as error:
        StoragePolicy.authorize(StorageOperation.DELETE, external)
    denial = error.value
    assert denial.code == "external_storage_operation_denied"
    assert (denial.operation, denial.storage_class, denial.storage_id) == (
        "delete",
        "external_read_only",
        "root:0",
    )
    assert vars(denial) == {
        "operation": "delete",
        "storage_class": "external_read_only",
        "storage_id": "root:0",
        "message": "delete denied for external_read_only storage root:0",
    }
    assert "/external" not in str(denial) and ".." not in str(denial)
    assert len(str(denial)) <= 160
