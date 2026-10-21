"""Isolated provider transport and observations around the actual RQ worker."""

import argparse
import json
import os
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from phase33_collection_fixture import authority  # noqa: E402

EVIDENCE = Path("/phase34/evidence")


def record(kind, **values):
    row = json.dumps({"kind": kind, **values}, sort_keys=True) + "\n"
    descriptor = os.open(
        EVIDENCE / "observations.jsonl", os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o644
    )
    try:
        os.write(descriptor, row.encode())
    finally:
        os.close(descriptor)


class Provider(BaseHTTPRequestHandler):
    def log_message(self, *_args):
        pass

    def do_GET(self):
        parsed = urlsplit(self.path)
        query = parse_qs(parsed.query)
        record("provider_http", endpoint=parsed.path, term=query.get("term", [""])[0])
        payload: dict[str, object] = (
            {"items": []}
            if parsed.path.endswith("storesearch")
            else {"results_html": ""}
        )
        data = json.dumps(payload).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


def install():
    import yarl

    from adapters.services import steam
    from handler import metadata
    from handler.database.scan_write_fence import current_scan_write_context
    from handler.filesystem import storage_access
    from handler.filesystem.roms_handler import FSRomsHandler
    from handler.filesystem.scan_media_publication import ScanMediaBatch
    from handler.metadata import meta_steam_handler
    from utils.rate_limiter import RateLimiter

    for name, handler in vars(metadata).items():
        if name.startswith("meta_") and hasattr(handler, "is_enabled"):
            handler.is_enabled = lambda: False
    patch.object(meta_steam_handler, "is_enabled", return_value=True).start()
    meta_steam_handler.steam_service.url = yarl.URL("http://127.0.0.1:3346/api")
    steam.STEAM_LIBRARY_CAPSULE_URL = "http://127.0.0.1:3346/capsule/{app_id}"
    steam._rate_limiter = RateLimiter(1000)

    def observe(kind):
        context = current_scan_write_context()
        record(kind, operation=context.operation_id if context else None)

    original_hash = storage_access.HashCapability.hash

    def hashing(self, *args, **kwargs):
        observe("hash")
        return original_hash(self, *args, **kwargs)

    patch.object(storage_access.HashCapability, "hash", hashing).start()
    original_descriptor = storage_access.hash_descriptor_file

    def descriptor_hash(*args, **kwargs):
        observe("hash")
        return original_descriptor(*args, **kwargs)

    storage_access.hash_descriptor_file = descriptor_hash
    original_components = FSRomsHandler.get_pc_components

    async def components(self, *args, **kwargs):
        observe("components")
        return await original_components(self, *args, **kwargs)

    patch.object(FSRomsHandler, "get_pc_components", components).start()
    original_prepare = ScanMediaBatch.prepare

    def preparing(self, *args, **kwargs):
        observe("media_prepare")
        return original_prepare(self, *args, **kwargs)

    patch.object(ScanMediaBatch, "prepare", preparing).start()
    from handler import scan_handler

    original_scan = scan_handler.scan_rom

    async def enrichment(*args, **kwargs):
        observe("enrichment")
        return await original_scan(*args, **kwargs)

    scan_handler.scan_rom = enrichment
    from handler.database import scan_inventory_state

    original_enlist = scan_inventory_state._enlist

    def enlist(session, binding, operation):
        try:
            return original_enlist(session, binding, operation)
        except Exception as error:
            import traceback

            record(
                "inventory_enlist_rejected",
                path=binding.game_relative_path,
                cause=str(error),
                trace=traceback.format_exc(),
            )
            raise

    scan_inventory_state._enlist = enlist
    from phase35_incremental_barrier import install as install_barriers

    install_barriers()
    record("worker_boot", pid=os.getpid())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("worker", "provider", "api"))
    args = parser.parse_args()
    authority()
    if sys.version_info < (3, 13):
        raise RuntimeError("backend runtime requires Python 3.13")
    if args.mode == "provider":
        ThreadingHTTPServer(("127.0.0.1", 3346), Provider).serve_forever()
    else:
        install()
        if args.mode == "api":
            import uvicorn

            uvicorn.run("main:app", host="127.0.0.1", port=3344)
        else:
            from handler.redis_handler import redis_client
            from handler.rq_worker import RomMWorker

            RomMWorker(["high", "default", "low"], connection=redis_client).work()


if __name__ == "__main__":
    main()
