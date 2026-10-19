"""Shared streaming resource preparation using existing storage capabilities."""

from pathlib import PurePosixPath

from handler.filesystem.storage_access import OwnedReplace, open_owned_access
from handler.filesystem.storage_policy import StorageOperation


async def store_resource(handler, url, path, allowed, *, cover_size=None, image=False):
    """Stream provider or local bytes before the short publication transaction."""
    from contextlib import ExitStack

    import httpx
    from anyio import open_file
    from PIL import Image

    from adapters.services.screenscraper import media_download_slot
    from config import ENABLE_SCHEDULED_CONVERT_IMAGES_TO_WEBP
    from handler.database.scan_write_fence import current_scan_write_context
    from handler.filesystem import resources_handler as resource_module
    from handler.filesystem.resources_handler import (
        LOCAL_FILE_SCHEMES,
        _check_content_type,
        _is_chroma_key_placeholder,
        _resolve_local_file_uri,
    )
    from handler.filesystem.scan_media_publication import (
        ensure_directory,
        require_scan_media_batch,
    )

    async def chunks():
        if url.startswith("file://") and current_scan_write_context() is not None:
            from handler.filesystem import get_fs_rom_handler

            with get_fs_rom_handler().open_rom_read(url[len("file://") :]) as access:
                with access.binary_file() as source:
                    while chunk := source.read(1024 * 1024):
                        yield chunk
            return
        if url.startswith(LOCAL_FILE_SCHEMES):
            resolved = _resolve_local_file_uri(url)
            if resolved is None:
                raise ValueError("scan_media_source_invalid")
            async with await open_file(resolved, "rb") as source:
                while chunk := await source.read(1024 * 1024):
                    yield chunk
        else:
            async with media_download_slot(url) as timeout:
                async with resource_module.ctx_httpx_client.get().stream(
                    "GET", url, timeout=timeout
                ) as response:
                    if response.status_code != 200 or not _check_content_type(
                        response, allowed, "resource"
                    ):
                        raise ValueError("scan_media_response_invalid")
                    import zlib

                    decoder = (
                        zlib.decompressobj(16 + zlib.MAX_WBITS)
                        if response.headers.get("content-encoding", "").lower()
                        == "gzip"
                        else None
                    )
                    async for chunk in response.aiter_raw():
                        if decoder is None:
                            yield chunk
                        else:
                            try:
                                while chunk:
                                    decoded = decoder.decompress(chunk, 1024 * 1024)
                                    chunk = decoder.unconsumed_tail
                                    if decoded:
                                        yield decoded
                            except zlib.error:
                                decoder = None
                                yield chunk

    if current_scan_write_context() is not None:
        unit = require_scan_media_batch()
        if cover_size and ENABLE_SCHEDULED_CONVERT_IMAGES_TO_WEBP:
            path = str(PurePosixPath(path).with_suffix(".webp"))
        output = unit.prepare(path)
        try:
            async for chunk in chunks():
                output.file.write(chunk)
                output.file.flush()
            output.file.flush()
            if image or cover_size:
                output.file.seek(0)
                if _is_chroma_key_placeholder(output.file):
                    raise ValueError("scan_media_chroma_key")
                output.file.seek(0)
                with Image.open(output.file) as original:
                    original.load()
                    transformed = original.copy()
                if cover_size == "small":
                    ratio = 0.2 if transformed.height >= 1000 else 0.4
                    transformed = transformed.resize(
                        (
                            max(1, int(transformed.width * ratio)),
                            max(1, int(transformed.height * ratio)),
                        )
                    )
                if cover_size:
                    transformed = handler.image_converter._convert_image_mode(
                        transformed
                    )
                    output.file.seek(0)
                    output.file.truncate()
                    transformed.save(
                        output.file, "WEBP" if path.endswith(".webp") else "PNG"
                    )
            unit.finish(output)
            return output.path
        except BaseException:
            output.capability.abort()
            raise
    directory, _filename = path.rsplit("/", 1)
    ensure_directory(handler.storage, directory)
    publishing = False
    try:
        with ExitStack() as stack:
            access = stack.enter_context(
                open_owned_access(handler.storage, StorageOperation.OVERWRITE, path)
            )
            assert isinstance(access, OwnedReplace)
            destination = stack.enter_context(access.binary_file())
            async for chunk in chunks():
                destination.write(chunk)
            destination.flush()
            if image or cover_size:
                destination.seek(0)
                if _is_chroma_key_placeholder(destination):
                    raise ValueError("resource_chroma_key")
                destination.seek(0)
                with Image.open(destination) as original:
                    original.load()
                    transformed = original.copy()
                if cover_size:
                    if cover_size == "small":
                        ratio = 0.2 if transformed.height >= 1000 else 0.4
                        transformed = transformed.resize(
                            (
                                max(1, int(transformed.width * ratio)),
                                max(1, int(transformed.height * ratio)),
                            )
                        )
                    destination.seek(0)
                    destination.truncate()
                    transformed.save(destination, "PNG")
                    if ENABLE_SCHEDULED_CONVERT_IMAGES_TO_WEBP:
                        webp = str(PurePosixPath(path).with_suffix(".webp"))
                        converted = stack.enter_context(
                            open_owned_access(
                                handler.storage, StorageOperation.OVERWRITE, webp
                            )
                        )
                        assert isinstance(converted, OwnedReplace)
                        target = stack.enter_context(converted.binary_file())
                        handler.image_converter._convert_image_mode(transformed).save(
                            target,
                            "WEBP",
                            quality=handler.image_converter.quality,
                            optimize=True,
                        )
            # Publication errors are not optional provider failures.
            publishing = True
        return path
    except (ValueError, OSError, httpx.TransportError):
        if publishing:
            raise
        return None
