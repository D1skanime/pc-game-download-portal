"""Loopback provider HTTP and delegating observations around actual application owners."""

import argparse
import hashlib
import json
import os
import sys
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from phase33_collection_fixture import authority
from phase35_incremental_worker import record
from phase36_description_fixture import TEXT

EVIDENCE = Path("/phase34/evidence")


class Provider(BaseHTTPRequestHandler):
    def log_message(self, *_args):
        pass

    def do_POST(self):
        parsed = urlsplit(self.path)
        content = self.rfile.read(int(self.headers.get("Content-Length", "0"))).decode()
        payload: Any
        if parsed.path == "/oauth":
            payload = {
                "access_token": os.environ["PHASE34_RUN_TOKEN"],
                "expires_in": 3600,
            }
        elif parsed.path == "/igdb/games":
            payload = [
                {
                    "id": 3070,
                    "name": "New IGDB",
                    "slug": "new-igdb",
                    "platforms": [{"id": 6, "name": "PC (Microsoft Windows)"}],
                    "external_games": [{"category": 1, "uid": "777"}],
                }
            ]
        else:
            payload = []
        record(
            "provider_http",
            provider="igdb",
            endpoint=parsed.path,
            query={},
            status=200,
            query_sha256=__import__("hashlib").sha256(content.encode()).hexdigest(),
        )
        wire_data = json.dumps(payload).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(wire_data)))
        self.end_headers()
        self.wfile.write(wire_data)

    def do_HEAD(self):
        record("capsule_http", endpoint=urlsplit(self.path).path)
        self.send_response(404)
        self.end_headers()

    def do_GET(self):
        parsed = urlsplit(self.path)
        query = parse_qs(parsed.query)
        safe = {
            key: value
            for key, value in query.items()
            if key
            in {
                "appids",
                "l",
                "cc",
                "term",
                "gameid",
                "recherche",
                "systemeid",
                "romnom",
            }
        }
        control = EVIDENCE / "provider-control.json"
        enabled = control.exists() and json.loads(control.read_text()).get("enabled")
        status = 200
        payload: dict[str, Any] = {}
        identity = int(query.get("appids", ["0"])[0])
        if enabled and parsed.path.endswith("appdetails"):
            if identity == 205:
                status = 429
            elif identity == 206:
                time.sleep(1.2)
            tag = {"german": "de", "french": "fr", "english": "en"}.get(
                query.get("l", [""])[0], "en"
            )
            text = TEXT[tag] + " " + str(identity)
            if identity == 201 and tag == "de" or identity == 204:
                text = ""
            if identity == 202:
                text = TEXT["en"] + " " + str(identity)
            if identity == 1245620 and json.loads(control.read_text()).get("markup"):
                text = "<img src=x onerror=alert(1)> " + text
            data = {
                "steam_appid": 999 if identity == 203 else identity,
                "type": "dlc" if 300 <= identity < 400 else "game",
                "fullgame": {"appid": 1245620, "name": "Known Game"},
                "name": "Known Game",
                "short_description": text,
                "detailed_description": text,
                "supported_languages": "English, German, French",
            }
            payload = {str(identity): {"success": True, "data": data}}
        elif enabled and parsed.path.endswith("storesearch"):
            payload = {"items": [{"type": "app", "id": 1245620, "name": "Known Game"}]}
        elif parsed.path.endswith("storesearch"):
            payload = {"items": []}
        elif enabled and parsed.path.endswith(("jeuInfos.php", "jeuRecherche.php")):
            game = {
                "id": query.get("gameid", ["38"])[0],
                "noms": [
                    {"region": "wor", "text": "Control"},
                    {"region": "ss", "text": "Control"},
                ],
                "synopsis": [
                    {"langue": tag, "text": text + " 38"} for tag, text in TEXT.items()
                ],
            }
            payload = (
                {"response": {"jeux": [game]}}
                if parsed.path.endswith("jeuRecherche.php")
                else {"response": {"jeu": game}}
            )
        if parsed.path.endswith("jeuInfos.php") and query.get("gameid") == ["39"]:
            status, payload = 429, {}
        wire_data = json.dumps(payload).encode()
        response_slots = []
        if parsed.path.endswith("appdetails") and status == 200 and payload:
            summary = (
                payload.get(str(identity), {})
                .get("data", {})
                .get("short_description", "")
            )
            response_slots = [
                {"summary_sha256": hashlib.sha256(summary.encode()).hexdigest()}
            ]
        elif (
            parsed.path.endswith(("jeuInfos.php", "jeuRecherche.php")) and status == 200
        ):
            games = payload.get("response", {}).get("jeux", [])
            if "jeu" in payload.get("response", {}):
                games = [payload["response"]["jeu"]]
            response_slots = [
                {
                    "source_language": slot["langue"],
                    "summary_sha256": hashlib.sha256(slot["text"].encode()).hexdigest(),
                }
                for game in games
                for slot in game.get("synopsis", [])
            ]
        record(
            "provider_http",
            response_sha256=hashlib.sha256(wire_data).hexdigest(),
            requested_language=query.get("l", [None])[0],
            response_text_variants=response_slots,
            provider=(
                "ss"
                if parsed.path.endswith(".php")
                else "libretro" if parsed.path.startswith("/libretro") else "steam"
            ),
            endpoint=parsed.path,
            query=safe,
            status=status,
        )
        wire_data = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(wire_data)))
        self.end_headers()
        try:
            self.wfile.write(wire_data)
        except BrokenPipeError:
            pass


def install():
    from unittest.mock import patch

    import aiohttp
    import httpx
    import yarl
    from phase35_incremental_worker import install as observed_install

    from adapters.services import screenscraper, steam
    from handler.metadata import (
        meta_igdb_handler,
        meta_libretro_handler,
        meta_ss_handler,
    )
    from utils.rate_limiter import RateLimiter

    observed_install()
    patch.object(meta_ss_handler, "is_enabled", return_value=True).start()
    meta_ss_handler.ss_service.url = yarl.URL("http://127.0.0.1:3346/api2")
    meta_libretro_handler.service.url = yarl.URL("http://127.0.0.1:3346/libretro")
    meta_igdb_handler.igdb_service.url = yarl.URL("http://127.0.0.1:3346/igdb")
    meta_igdb_handler.igdb_service.twitch_auth.BASE_URL = "http://127.0.0.1:3346/oauth"

    def igdb_enabled():
        path = EVIDENCE / "provider-control.json"
        return path.exists() and json.loads(path.read_text()).get("igdb", False)

    patch.object(meta_igdb_handler, "is_enabled", side_effect=igdb_enabled).start()
    patch.object(steam, "STEAM_RATE_LIMIT_BACKOFF_SECONDS", 0.05).start()
    screenscraper._rate_limiter = RateLimiter(1000)
    original = aiohttp.ClientSession._request

    async def guarded(self, method, url, *args, **kwargs):
        parsed = urlsplit(str(url))
        if (
            parsed.scheme != "http"
            or parsed.hostname != "127.0.0.1"
            or parsed.port != 3346
        ):
            raise RuntimeError("provider egress outside owned loopback refused")
        return await original(self, method, url, *args, **kwargs)

    patch.object(aiohttp.ClientSession, "_request", guarded).start()
    original_httpx = httpx.AsyncClient.send

    async def guarded_httpx(self, request, *args, **kwargs):
        parsed = urlsplit(str(request.url))
        if (parsed.scheme, parsed.hostname, parsed.port) != ("http", "127.0.0.1", 3346):
            raise RuntimeError("provider httpx egress outside owned loopback refused")
        return await original_httpx(self, request, *args, **kwargs)

    patch.object(httpx.AsyncClient, "send", guarded_httpx).start()
    original_steam = steam.SteamService._request

    async def bounded(self, url, request_timeout=120):
        return await original_steam(self, url, request_timeout=1)

    patch.object(steam.SteamService, "_request", bounded).start()
    from handler import scan_description_retry

    original_dispatch = scan_description_retry.dispatch_description

    async def dispatch(coordinator, work, identity):
        record(
            "description_dispatch",
            provider=identity.provider,
            rom_id=work.rom_id,
            component=coordinator.description_targets[identity.key].component_id,
            locale=coordinator.policy["metadata_locale"],
        )
        return await original_dispatch(coordinator, work, identity)

    scan_description_retry.dispatch_description = dispatch
    if (EVIDENCE / "enable-authority").exists():
        from phase36_description_authority import install as install_authority

        install_authority()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("provider", "api", "worker"))
    args = parser.parse_args()
    authority()
    if args.mode == "provider":
        ThreadingHTTPServer(("127.0.0.1", 3346), Provider).serve_forever()
        return
    install()
    if args.mode == "api":
        import uvicorn

        uvicorn.run("main:app", host="127.0.0.1", port=3344)
    else:
        from handler.redis_handler import redis_client
        from handler.rq_worker import RomMWorker

        record("description_worker_boot", pid=os.getpid())
        RomMWorker(["high", "default", "low"], connection=redis_client).work()


if __name__ == "__main__":
    main()
