"""Authoritative durable operation transitions, independent of presentation state."""

STATES = (
    "accepted",
    "queued",
    "running",
    "stopping",
    "cancelled",
    "interrupted",
    "recovering",
    "blocked",
    "failed",
    "completed",
    "completed-with-warnings",
)
TERMINAL = frozenset({"cancelled", "failed", "completed", "completed-with-warnings"})
TRANSITIONS = {
    "accepted": {"queued", "stopping", "blocked", "failed"},
    "queued": {"running", "stopping", "interrupted", "blocked", "failed"},
    "running": {
        "stopping",
        "interrupted",
        "blocked",
        "failed",
        "completed",
        "completed-with-warnings",
    },
    "stopping": {"cancelled", "interrupted"},
    "interrupted": {"recovering", "stopping", "blocked", "failed"},
    "recovering": {"queued", "running", "stopping", "blocked", "failed", "interrupted"},
    "blocked": {"recovering", "stopping", "failed"},
    "cancelled": {"recovering"},
    "failed": {"recovering"},
    "completed": set(),
    "completed-with-warnings": {"recovering"},
}


def validate_transition(
    source: str,
    target: str,
    *,
    lease: bool,
    confirmed_stop: bool,
    explicit_resume: bool = False,
) -> None:
    if target not in TRANSITIONS.get(source, set()):
        raise ValueError("invalid_transition")
    if target == "running" and not lease:
        raise ValueError("lease_required")
    if target == "cancelled" and not confirmed_stop:
        raise ValueError("stop_not_confirmed")
    if source in TERMINAL and target == "recovering" and not explicit_resume:
        raise ValueError("explicit_resume_required")
