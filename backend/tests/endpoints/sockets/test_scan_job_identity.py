"""Actual RQ callable identity regressions. No scanner or worker executes."""

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from rq.job import Job, JobStatus
from tools.phase34_target_guard import validate_target

from endpoints.sockets import scan


@pytest.fixture
def jobs(monkeypatch):
    validate_target()
    created = []
    monkeypatch.setattr(scan.Worker, "all", lambda **kwargs: [])
    monkeypatch.setattr(scan.tasks_scheduler, "get_jobs", lambda: [])

    def create(func):
        job = Job.create(
            func=func, connection=scan.redis_client, status=JobStatus.QUEUED
        )
        job.save()
        created.append(job)
        return job

    yield create
    validate_target()
    for job in created:
        job.delete()
    scan.redis_client.delete(scan.STOP_SCAN_FLAG)


def running(monkeypatch, job):
    worker = SimpleNamespace(get_current_job=lambda: job)
    monkeypatch.setattr(scan.Worker, "all", lambda **kwargs: [worker])


def test_real_disposable_redis_ready(jobs):
    assert scan.redis_client.ping()
    job = jobs(scan.execute_mixed_scans)
    fetched = Job.fetch(job.id, connection=scan.redis_client)
    assert fetched.func is scan.execute_mixed_scans
    assert fetched.func_name == "endpoints.sockets.scan.execute_mixed_scans"


def test_manual_running_job_is_recognized(jobs, monkeypatch):
    job = jobs(scan.execute_mixed_scans)
    running(monkeypatch, job)
    assert (
        scan._get_running_scan_job() is job
    ), "P34_RQ_RUNNING: actual manual callable is invisible"


def test_manual_queued_job_is_recognized(jobs):
    job = jobs(scan.execute_mixed_scans)
    scan.high_prio_queue.enqueue_job(job)
    found = scan._get_queued_scan_jobs()
    assert job.id in {
        item.id for item in found
    }, "P34_RQ_QUEUED: real queued manual callable is invisible"


@pytest.mark.asyncio
async def test_stop_finds_manual_job(jobs, monkeypatch):
    job = jobs(scan.execute_mixed_scans)
    running(monkeypatch, job)
    monkeypatch.setattr(scan, "reject_unauthorized_scan", AsyncMock(return_value=False))
    await scan.stop_scan_handler("phase34-authorized-fixture")
    fetched = Job.fetch(job.id, connection=scan.redis_client)
    assert (
        fetched.get_status() == JobStatus.CANCELED
    ), "P34_RQ_STOP: stop lookup misses real manual callable"
    assert scan.redis_client.get(scan.STOP_SCAN_FLAG) == b"1"


@pytest.mark.parametrize("family", ["watcher", "scheduled"])
def test_existing_scan_family_controls(jobs, monkeypatch, family):
    func = scan.scan_platforms if family == "watcher" else scan.SCAN_LIBRARY_TASK_FUNC
    job = jobs(func)
    assert isinstance(job, Job)
    running(monkeypatch, job)
    found = scan._get_running_scan_job()
    assert found is not None
    assert found.id == job.id
    scan.low_prio_queue.enqueue_job(job)
    assert job.id in {item.id for item in scan._get_queued_scan_jobs()}
