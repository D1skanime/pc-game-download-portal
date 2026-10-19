from pathlib import Path
from types import SimpleNamespace

import pytest

from handler.setup_folder_handler import SetupFolderHandler


def _root(path: Path):
    return SimpleNamespace(id=7, name="Games", container_path=str(path), active=True)


def test_root_registers_configured_library_when_database_is_empty(
    monkeypatch, tmp_path
):
    import handler.setup_folder_handler as setup_module

    registered = _root(tmp_path)
    monkeypatch.setattr(setup_module, "LIBRARY_BASE_PATH", str(tmp_path))
    monkeypatch.setattr(setup_module.db_storage_handler, "get_roots", lambda: [])
    calls = []

    def register_root(name, container_path):
        calls.append((name, container_path))
        return registered

    monkeypatch.setattr(setup_module.db_storage_handler, "register_root", register_root)

    result = SetupFolderHandler().root()

    assert result is registered
    assert calls == [(setup_module.ROOT_LABEL, str(tmp_path))]


def test_resolve_platform_bootstraps_missing_supported_platform(monkeypatch, tmp_path):
    import handler.setup_folder_handler as setup_module

    option = SimpleNamespace(
        slug="win",
        fs_slug="win",
        name="Windows",
    )
    monkeypatch.setattr(
        setup_module.SetupFolderHandler,
        "_platform_options",
        staticmethod(lambda: [option]),
    )
    monkeypatch.setattr(
        setup_module.db_platform_handler,
        "get_platform_by_slug",
        lambda slug: None,
    )
    monkeypatch.setattr(
        setup_module.db_platform_handler,
        "get_platform_by_fs_slug",
        lambda fs_slug: None,
    )
    created = []

    def add_platform(platform):
        created.append(platform)
        return SimpleNamespace(id=9, slug=platform.slug)

    monkeypatch.setattr(
        setup_module.db_platform_handler,
        "add_platform",
        add_platform,
    )

    result = SetupFolderHandler()._resolve_platform("win")

    assert result.id == 9
    assert created[0].name == "Windows"
    assert created[0].slug == "win"
    assert created[0].fs_slug == "win"

    (tmp_path / "My Games").mkdir()
    (tmp_path / "Windows").mkdir()
    (tmp_path / "ignored.txt").write_text("source")
    supported = [
        SimpleNamespace(slug="win", name="Windows", fs_slug="win"),
        SimpleNamespace(slug="switch", name="Nintendo Switch", fs_slug="switch"),
    ]
    monkeypatch.setattr(
        "handler.setup_folder_handler.get_supported_platforms", lambda: supported
    )
    handler = SetupFolderHandler()

    result = handler.discover(_root(tmp_path))

    assert [folder.relative_path for folder in result.folders] == [
        "My Games",
        "Windows",
    ]
    assert result.folders[0].association == "unknown"
    assert result.folders[1].suggested_platform == "win"
    assert all(str(tmp_path) not in folder.relative_path for folder in result.folders)


@pytest.mark.parametrize("name", ["../escape", "/absolute", "C:\\games", "a/b"])
def test_discovery_rejects_unsafe_folder_names(tmp_path, monkeypatch, name):
    class Entry:
        def __init__(self):
            self.name = name

        def is_dir(self, *, follow_symlinks=False):
            return True

        def is_symlink(self):
            return False

    monkeypatch.setattr(Path, "iterdir", lambda _: iter([Entry()]))
    monkeypatch.setattr(
        "handler.setup_folder_handler.get_supported_platforms", lambda: []
    )

    with pytest.raises(ValueError, match="safe"):
        SetupFolderHandler().discover(_root(tmp_path))


def test_assignment_requires_every_row_and_returns_idempotent_mappings(monkeypatch):
    handler = SetupFolderHandler()
    folders = [SimpleNamespace(name="Windows", relative_path="Windows")]
    monkeypatch.setattr(
        handler, "discover", lambda root: SimpleNamespace(folders=folders)
    )
    monkeypatch.setattr(
        handler, "_resolve_platform", lambda slug: SimpleNamespace(id=5, slug=slug)
    )
    monkeypatch.setattr(
        handler,
        "_root_health",
        lambda root: SimpleNamespace(reachable=True, readable=True, non_writable=True),
    )
    saved = SimpleNamespace(id=11, relative_path="Windows")
    monkeypatch.setattr(
        handler, "_reconcile", lambda root, platform, path, actor: saved
    )
    monkeypatch.setattr(
        "handler.setup_folder_handler.db_storage_handler.get_active_mapping",
        lambda platform_id: (_ for _ in ()).throw(Exception("missing")),
    )
    monkeypatch.setattr(
        "handler.setup_folder_handler.MissingPlatformStorageMappingError",
        Exception,
    )
    monkeypatch.setattr(
        "handler.setup_folder_handler.db_storage_handler.test_mapping",
        lambda *args, **kwargs: saved,
    )
    root = _root(Path("/games"))

    result = handler.assign(
        root, [{"folder_name": "Windows", "platform_slug": "win"}], actor={}
    )

    assert result.ready is True
    assert result.mappings[0]["mapping_id"] == 11
    with pytest.raises(ValueError, match="every"):
        handler.assign(root, [], actor={})
