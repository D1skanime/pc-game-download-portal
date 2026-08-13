from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from config import TASK_TIMEOUT
from handler.storage.legacy_migration import LEGACY_OBSERVATION_DEADLINE_SECONDS
from tasks.manual import detect_legacy_storage as subject


class FakeMonotonic:
    def __init__(self, elapsed: float) -> None:
        self.elapsed = elapsed
        self.first = True

    def __call__(self) -> float:
        if self.first:
            self.first = False
            return 0.0
        return self.elapsed


@pytest.mark.parametrize(
    ("elapsed", "selectable", "problem"),
    [(239.0, True, None), (240.0, False, "time_budget")],
)
async def test_task_persists_safe_result_at_239_and_cancels_at_240(
    tmp_path, monkeypatch, elapsed, selectable, problem
):
    canonical = tmp_path / "roms" / "gb"
    canonical.mkdir(parents=True)
    source = canonical / "private.rom"
    source.write_bytes(b"private-bytes")
    context = SimpleNamespace(
        platform_id=5,
        storage_root_id=7,
        fs_slug="gb",
        container_path=str(tmp_path),
        root_active=True,
    )
    saved: dict[str, Any] = {}

    class FakeHandler:
        def get_detection_context(self, platform_id, storage_root_id):
            assert (platform_id, storage_root_id) == (5, 7)
            return context

        def save_detection_result(self, saved_context, outcome, **kwargs):
            saved.update(context=saved_context, outcome=outcome, kwargs=kwargs)
            return SimpleNamespace(id=19)

    monkeypatch.setattr(subject, "DBLegacyMigrationHandler", FakeHandler)
    monkeypatch.setattr(subject, "monotonic", FakeMonotonic(elapsed))

    result_id = await subject.detect_legacy_storage_task.run(5, 7, 11)

    assert result_id == 19
    assert saved["context"] is context
    assert saved["kwargs"] == {"actor_user_id": 11}
    assert saved["outcome"].selectable is selectable
    assert saved["outcome"].safe_problem_code == problem
    assert (saved["outcome"].source_fingerprint is not None) is selectable
    assert str(tmp_path) not in str(saved["outcome"])
    source.rename(canonical / "closed.rom")


def test_task_deadline_leaves_persistence_margin():
    assert LEGACY_OBSERVATION_DEADLINE_SECONDS == 240
    assert subject.detect_legacy_storage_task.timeout == TASK_TIMEOUT == 300
    assert subject.detect_legacy_storage_task.timeout - 240 == 60
