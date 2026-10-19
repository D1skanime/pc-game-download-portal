"""Acquire the shared owned writer domain before higher-level transactions."""

from functools import wraps


def serialized_owned_write(function):
    @wraps(function)
    def wrapped(*args, **kwargs):
        from handler.filesystem.owned_writer_domain import owned_writer_domain

        with owned_writer_domain():
            return function(*args, **kwargs)

    return wrapped
