from types import SimpleNamespace

import pytest

from handler import scan_operation_checkpoint as checkpoint


def test_integer_cursor_cannot_authorize_automatic_recovery():
    with pytest.raises(checkpoint.SourceEvidenceRejected):
        checkpoint.validate_recovery_checkpoint(
            {"checkpoint": {"schema": 1, "cursor": "100"}}
        )


def test_forged_generation_without_authoritative_validator_is_rejected():
    execution = {"checkpoint": {"schema": 1, "source_generation": "client-string"}}
    with pytest.raises(checkpoint.SourceEvidenceRejected):
        checkpoint.validate_recovery_checkpoint(execution)


def test_authoritative_immutable_generation_can_prove_fixture():
    execution = {
        "checkpoint": {"schema": 1, "source_generation": "immutable-fixture-v1"}
    }
    assert checkpoint.validate_recovery_checkpoint(
        execution,
        generation_validator=lambda saved: saved["checkpoint"]["source_generation"]
        == "immutable-fixture-v1",
    )


def test_same_size_changed_content_rejects_game_retry(monkeypatch):
    command = SimpleNamespace(mapping_id=1, expected_revision=2)
    info = SimpleNamespace(
        st_dev=1, st_ino=2, st_size=3, st_mtime_ns=4, st_ctime_ns=5, st_mode=0o100644
    )

    class Capability:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def stat(self):
            return info

        def hash(self, algorithm):
            return "changed-digest"

    context = SimpleNamespace(validate=lambda: None, open=lambda *args: Capability())
    monkeypatch.setattr(checkpoint, "MappingReadContext", lambda *args: context)
    with pytest.raises(checkpoint.SourceEvidenceRejected, match="source_changed"):
        checkpoint.validate_game_evidence(
            command,
            {
                "schema": 1,
                "mapping_id": 1,
                "revision": 2,
                "target": "game.bin",
                "files": [{"path": "game.bin", "size": 3, "sha1": "old-digest"}],
            },
        )


def test_missing_hashes_are_not_mislabeled_as_verifiable():
    command = SimpleNamespace(mapping_id=1, expected_revision=2, options=())
    rom = SimpleNamespace(fs_path="roms/win", fs_name="game.bin")
    file = SimpleNamespace(full_path="roms/win/game.bin", sha1_hash=None)
    assert checkpoint.game_file_evidence(command, rom, [file]) == {"verifiable": False}


def test_scoped_game_evidence_uses_mapping_relative_child_once():
    command = SimpleNamespace(
        mapping_id=1,
        expected_revision=2,
        options=(("relative_path", "Castlevania/Belmonts.Curse"),),
    )
    rom = SimpleNamespace(fs_path="pc-Games/Castlevania", fs_name="Belmonts.Curse")
    file = SimpleNamespace(
        full_path="pc-Games/Castlevania/Belmonts.Curse/game.rar",
        sha1_hash="digest",
        file_size_bytes=4,
    )
    evidence = checkpoint.game_file_evidence(command, rom, [file])
    assert evidence["target"] == "Castlevania/Belmonts.Curse"
    assert evidence["files"][0]["path"] == "Castlevania/Belmonts.Curse/game.rar"
