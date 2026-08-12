from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .read_context import MappingReadContext

__all__ = ["MappingReadContext"]


def __getattr__(name: str) -> Any:
    if name != "MappingReadContext":
        raise AttributeError(name)
    from .read_context import MappingReadContext

    return MappingReadContext
