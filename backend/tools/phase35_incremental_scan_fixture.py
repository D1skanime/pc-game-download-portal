"""Generated synthetic library and explicit edits between immutable segments."""

import json
import os
import re
import shutil
import tempfile
from pathlib import Path

from phase34_fixtures import prepare as original_prepare
from phase34_fixtures import source_manifest


def manifest(root):
    if root.is_symlink():
        root = root.resolve()
    if any(path.is_symlink() for path in root.rglob("*")):
        raise RuntimeError("fixture source symlink refused")
    return source_manifest(root)


def assert_immutable(root, before):
    if manifest(root) != before:
        raise RuntimeError("application changed fixture source")


def owned_root(root):
    if (
        root.parent.resolve() != Path(tempfile.gettempdir()).resolve()
        or not re.fullmatch(r"pgdp34-[a-f0-9]{32}-.+", root.name)
        or root.is_symlink()
    ):
        raise RuntimeError("unowned fixture root")


def prepare(root, repo):
    owned_root(root)
    games, checkout = original_prepare(root, repo)
    if games.resolve() != root / "Games" or games.is_symlink():
        raise RuntimeError("unexpected generated fixture")
    shutil.rmtree(games)
    fixture = root / "fixture/Games"
    names = ["Known.Game", "Castlevania/Belmonts.Curse", "Castlevania/Lords.of.Shadow2"]
    names += ["Unknown" + str(index) for index in range(6)]
    for name in names:
        folder = fixture / "pc" / name / "Base"
        folder.mkdir(parents=True)
        (folder / "game.bin").write_bytes(("synthetic " + name).encode())
    control = fixture / "My Games"
    control.mkdir()
    (control / "Control.sfc").write_bytes(b"synthetic SNES control")
    games.symlink_to(fixture, target_is_directory=True)
    return games, checkout


def edit(root, action):
    owned_root(root)
    if action not in {"add", "change", "delete", "new-game", "new-child"}:
        raise RuntimeError("unknown fixture edit")
    fixture = root / "fixture/Games"
    game = fixture / "pc/Known.Game"
    if not game.is_dir() or game.is_symlink():
        raise RuntimeError("missing generated fixture")
    timestamp = game.stat()
    content = game / "DLC/Expansion/content.bin"
    if action == "add":
        content.parent.mkdir(parents=True)
        content.write_bytes(b"synthetic DLC")
    elif action == "change":
        content.write_bytes(b"synthetic DLC changed")
    elif action == "delete":
        content.unlink()
    else:
        relative = "New.Game" if action == "new-game" else "Castlevania/New.Child"
        folder = fixture / "pc" / relative / "Base"
        folder.mkdir(parents=True)
        (folder / "game.bin").write_bytes(("synthetic " + action).encode())
    os.utime(game, ns=(timestamp.st_atime_ns, timestamp.st_mtime_ns))
    return manifest(fixture)


def segment_edit(run, action):
    assert_immutable(run.root / "Games", run.before)
    before = run.before
    after = edit(run.root, action)
    receipt = {"action": action, "before": before, "after": after}
    (run.evidence / ("edit-" + action + ".json")).write_text(
        json.dumps(receipt, indent=2)
    )
    run.before = after
    (run.evidence / "source-before.json").write_text(json.dumps(after, indent=2))
