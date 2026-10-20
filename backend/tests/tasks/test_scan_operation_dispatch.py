from types import SimpleNamespace
from unittest.mock import Mock

from redis.exceptions import ConnectionError
from rq.exceptions import NoSuchJobError
from rq.job import JobStatus

from tasks import scan_operation_dispatch as dispatch


class Repository:
    def __init__(self):
        self.state = {"state": "accepted", "version": 1, "dispatch_due": True}
        self.failed = []
        self.enqueued = []

    def execution(self, identity):
        return dict(self.state)

    def claim_dispatch(self, identity, version, owner):
        self.owner = owner
        return SimpleNamespace(job_id="scan-fixture", version=2)

    def mark_enqueued(self, identity, version, owner):
        self.enqueued.append((identity, owner))
        self.state.update(state="queued", dispatch_due=None)

    def dispatch_failed(self, identity, owner):
        self.failed.append((identity, owner))


def test_acceptance_gap_dispatches_deterministic_job_once(monkeypatch):
    repository = Repository()
    queue = SimpleNamespace(connection=object(), enqueue=Mock())
    monkeypatch.setattr(dispatch.Job, "fetch", Mock(side_effect=NoSuchJobError))
    assert dispatch.dispatch_operation("operation", repository=repository, queue=queue)
    assert not dispatch.dispatch_operation(
        "operation", repository=repository, queue=queue
    )
    queue.enqueue.assert_called_once()
    assert queue.enqueue.call_args.kwargs["job_id"] == "scan-fixture"
    assert queue.enqueue.call_args.kwargs["operation_id"] == "operation"


def test_enqueue_before_ack_crash_recognizes_exact_existing_job(monkeypatch):
    repository = Repository()
    queue = SimpleNamespace(connection=object(), enqueue=Mock())
    job = SimpleNamespace(
        func_name=dispatch.WORKER_FUNC,
        kwargs={"operation_id": "operation"},
        get_status=lambda **kwargs: JobStatus.QUEUED,
    )
    monkeypatch.setattr(dispatch.Job, "fetch", Mock(return_value=job))
    assert dispatch.dispatch_operation("operation", repository=repository, queue=queue)
    queue.enqueue.assert_not_called()
    assert repository.enqueued


def test_redis_failure_retains_recoverable_intent(monkeypatch):
    repository = Repository()
    queue = SimpleNamespace(connection=object(), enqueue=Mock())
    monkeypatch.setattr(dispatch.Job, "fetch", Mock(side_effect=ConnectionError))
    assert not dispatch.dispatch_operation(
        "operation", repository=repository, queue=queue
    )
    assert repository.failed
    assert repository.state["state"] == "accepted"


def test_job_identity_collision_is_never_acknowledged(monkeypatch):
    repository = Repository()
    queue = SimpleNamespace(connection=object(), enqueue=Mock())
    job = SimpleNamespace(func_name="other.function", kwargs={})
    monkeypatch.setattr(dispatch.Job, "fetch", Mock(return_value=job))
    assert not dispatch.dispatch_operation(
        "operation", repository=repository, queue=queue
    )
    assert repository.failed
    assert not repository.enqueued
