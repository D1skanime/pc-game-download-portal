from dataclasses import FrozenInstanceError, replace
from pathlib import Path
from unittest.mock import patch

import pytest

from handler.filesystem.base_handler import FSHandler
from handler.filesystem.storage_composition import (
    OWNED_STORAGE_PATHS,
    StorageCompositionConfig,
    build_storage_composition,
)
from handler.filesystem.storage_policy import (
    ExternalStorageDescriptor,
    OwnedStorageDescriptor,
    OwnedStorageKind,
)

EXPECTED_OWNED_KINDS = frozenset(OwnedStorageKind)


def _config(
    tmp_path: Path, *, external: Path | None = None
) -> StorageCompositionConfig:
    external_root = external or tmp_path / "external"
    owned = {kind: tmp_path / "owned" / kind.value for kind in EXPECTED_OWNED_KINDS}
    return StorageCompositionConfig(
        library_base_path=external_root,
        owned_paths=owned,
    )


def test_composition_classifies_every_closed_owned_location(tmp_path: Path) -> None:
    composition = build_storage_composition(_config(tmp_path))

    assert set(composition.owned) == EXPECTED_OWNED_KINDS
    assert set(OWNED_STORAGE_PATHS) == EXPECTED_OWNED_KINDS
    assert all(
        isinstance(descriptor, OwnedStorageDescriptor) and descriptor.kind is kind
        for kind, descriptor in composition.owned.items()
    )
    assert isinstance(composition.legacy_external, ExternalStorageDescriptor)
    assert composition.legacy_external.mapping_id is None


@pytest.mark.parametrize(
    ("external_parts", "owned_parts"),
    [
        (("shared",), ("shared",)),
        (("shared", "library"), ("shared",)),
        (("shared",), ("shared", "resources")),
    ],
)
def test_overlap_fails_before_filesystem_observation(
    tmp_path: Path,
    external_parts: tuple[str, ...],
    owned_parts: tuple[str, ...],
) -> None:
    external = tmp_path.joinpath(*external_parts)
    config = _config(tmp_path, external=external)
    owned = dict(config.owned_paths)
    owned[OwnedStorageKind.RESOURCES] = tmp_path.joinpath(*owned_parts)
    overlapping = replace(config, owned_paths=owned)

    forbidden = AssertionError("filesystem observation or handler construction")
    with (
        patch.object(Path, "resolve", side_effect=forbidden),
        patch.object(Path, "mkdir", side_effect=forbidden),
        patch.object(Path, "stat", side_effect=forbidden),
        patch.object(Path, "open", side_effect=forbidden),
        patch("os.scandir", side_effect=forbidden),
        patch("tempfile.mkstemp", side_effect=forbidden),
        pytest.raises(ValueError, match="must be disjoint"),
    ):
        build_storage_composition(overlapping)


def test_arbitrary_path_text_cannot_forge_or_replace_external_identity(
    tmp_path: Path,
) -> None:
    composition = build_storage_composition(_config(tmp_path))
    descriptor = composition.legacy_external

    with pytest.raises(TypeError):
        ExternalStorageDescriptor(object(), 0, None)
    with pytest.raises((FrozenInstanceError, AttributeError)):
        descriptor.root_id = 99  # type: ignore[misc]
    assert not hasattr(composition, "replace_external")
    assert not hasattr(composition, "classify_path")


def test_fs_handler_requires_matching_owned_descriptor(tmp_path: Path) -> None:
    composition = build_storage_composition(_config(tmp_path))
    owned = composition.owned[OwnedStorageKind.RESOURCES]

    handler = FSHandler(tmp_path / "owned" / "resources", owned)
    assert handler.storage is owned

    with pytest.raises(TypeError, match="owned storage descriptor"):
        FSHandler(tmp_path / "external", composition.legacy_external)  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="owned storage descriptor"):
        FSHandler(tmp_path / "unclassified", None)  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="does not match"):
        FSHandler(tmp_path / "elsewhere", owned)
