"""Server-side ROM patching helpers.

Shells out to the sibling ``patcher.js`` (Node.js + RomPatcher.js) to apply
a patch file to a ROM file.
"""

import asyncio
import json
from pathlib import Path

from config import ROM_PATCHER_MAX_CONCURRENCY, ROM_PATCHER_TIMEOUT
from handler.filesystem.storage_access import OwnedCreate, OwnedRead, ReadCapability

PATCHER_SCRIPT = Path(__file__).parent / "patcher.js"

SUPPORTED_PATCH_EXTENSIONS = frozenset(
    (".ips", ".ups", ".bps", ".ppf", ".rup", ".aps", ".bdf", ".pmsr", ".vcdiff")
)

# Bound concurrent node subprocesses, each of which loads a full ROM into memory.
_patch_semaphore = asyncio.Semaphore(ROM_PATCHER_MAX_CONCURRENCY)


class PatcherError(Exception):
    """Raised when the Node.js patcher script fails or produces no output."""


async def apply_patch(
    rom: ReadCapability, patch: ReadCapability | OwnedRead, output: OwnedCreate
) -> bool:
    """Apply a patch through closed read and create capabilities.

    Returns whether the patch's embedded source checksum matched the ROM (always
    ``True`` for formats that carry no source checksum). The patch is applied
    regardless; the result lets callers warn on a likely ROM/patch mismatch.

    Raises :class:`PatcherError` if the subprocess fails, times out, or the
    output file is missing.
    """
    if (
        not isinstance(rom, ReadCapability)
        or not isinstance(patch, (ReadCapability, OwnedRead))
        or not isinstance(output, OwnedCreate)
    ):
        raise TypeError("patching requires read inputs and an owned create output")

    async with _patch_semaphore:
        with output.subprocess_file() as output_fd:
            descriptors = (rom.fileno(), patch.fileno(), output_fd)
            proc = await asyncio.create_subprocess_exec(
                "node",
                str(PATCHER_SCRIPT),
                *(f"/proc/self/fd/{descriptor}" for descriptor in descriptors),
                pass_fds=descriptors,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            try:
                stdout, stderr = await asyncio.wait_for(
                    proc.communicate(), timeout=ROM_PATCHER_TIMEOUT
                )
            except (asyncio.TimeoutError, TimeoutError) as e:
                proc.kill()
                await proc.wait()
                raise PatcherError(
                    f"Patching timed out after {ROM_PATCHER_TIMEOUT}s"
                ) from e

    if proc.returncode != 0:
        message = "Patching failed"
        try:
            err_data = json.loads(stderr.decode())
            message = err_data.get("error", message)
        except (json.JSONDecodeError, UnicodeDecodeError):
            if stderr:
                message = stderr.decode(errors="replace").strip()
        raise PatcherError(message)

    # The script reports source-checksum validation in its JSON stdout.
    try:
        result = json.loads(stdout.decode())
        return bool(result.get("validated", True))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return True
