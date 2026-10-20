"""Deterministic HTTPX bodies and real owned-file fixtures for download faults."""

from contextlib import asynccontextmanager
from io import BytesIO
from typing import TypedDict

import httpx
import pytest
from PIL import Image

from handler.filesystem import fs_resource_handler
from utils.context import ctx_httpx_client


def png_bytes():
    content = BytesIO()
    Image.new("RGB", (20, 30), (45, 65, 85)).save(content, "PNG")
    return content.getvalue()


class Body(httpx.AsyncByteStream):
    def __init__(self, chunks, fault=None):
        self.chunks = chunks
        self.fault = fault

    async def __aiter__(self):
        for chunk in self.chunks:
            yield chunk
        if self.fault:
            raise self.fault("deterministic provider stream fault")


@asynccontextmanager
async def provider_response(
    *, data=None, failure=None, mime="image/png", encoding=None
):
    data = png_bytes() if data is None else data

    def respond(request):
        if failure == "connect":
            raise httpx.ConnectError("deterministic connect fault", request=request)
        headers = {"content-type": "text/html" if failure == "mime" else mime}
        if encoding:
            headers["content-encoding"] = encoding
        fault = {"read": httpx.ReadError, "timeout": httpx.ReadTimeout}.get(failure)
        return httpx.Response(
            503 if failure == "status" else 200,
            headers=headers,
            stream=Body([data[:10], data[10:]], fault),
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
        token = ctx_httpx_client.set(client)
        try:
            yield client
        finally:
            ctx_httpx_client.reset(token)


class PrimaryPaths(TypedDict):
    path_cover_s: str
    path_cover_l: str
    path_manual: str
    path_screenshots: list[str]


async def seed_primary(rom):
    paths: PrimaryPaths = {
        "path_cover_s": f"{rom.fs_resources_path}/cover/small.png",
        "path_cover_l": f"{rom.fs_resources_path}/cover/big.png",
        "path_manual": f"{rom.fs_resources_path}/manual/{rom.id}.pdf",
        "path_screenshots": [f"{rom.fs_resources_path}/screenshots/0.jpg"],
    }
    for path in [
        paths["path_cover_s"],
        paths["path_cover_l"],
        paths["path_manual"],
        *paths["path_screenshots"],
    ]:
        directory, filename = path.rsplit("/", 1)
        await fs_resource_handler.write_file(b"prior good bytes", directory, filename)
    return paths


def resource_snapshot(rom):
    root = fs_resource_handler.validate_path(rom.fs_resources_path)
    return {
        str(path.relative_to(root)): path.read_bytes()
        for path in root.rglob("*")
        if path.is_file()
    }


@pytest.fixture(autouse=True)
def owned_resource_files(rom):
    """Retire only new files created under this test's exact owned ROM path."""
    root = fs_resource_handler.validate_path(rom.fs_resources_path)
    previous = {path for path in root.rglob("*") if path.is_file()}
    try:
        yield
    finally:
        for path in root.rglob("*"):
            if path.is_file() and path not in previous:
                path.unlink()
