import asyncio

import httpx
import pytest

from utils.scan_provider_observation import (
    bind_provider_observation,
    current_provider_observation,
    mark_provider_cached,
    mark_provider_invoked,
    observe_aiohttp_headers,
    observe_httpcore_trace,
    observe_retry_after,
)


@pytest.mark.asyncio
async def test_concurrent_scopes_keep_game_provider_and_counts_isolated():
    async def work(game, provider, count):
        with bind_provider_observation(provider, game) as observation:
            mark_provider_invoked()
            for _ in range(count):
                await asyncio.sleep(0)
                await observe_httpcore_trace("http11.send_request_headers.started", {})
            assert current_provider_observation() is observation
            return observation

    first, second = await asyncio.gather(
        work("one", "igdb", 2), work("two", "steam", 3)
    )
    assert (first.game, first.provider, first.requests) == ("one", "igdb", 2)
    assert (second.game, second.provider, second.requests) == ("two", "steam", 3)
    assert current_provider_observation() is None


@pytest.mark.asyncio
async def test_noop_cache_and_http_attempts_are_distinct():
    with bind_provider_observation("igdb", "game") as noop:
        pass
    with bind_provider_observation("igdb", "game") as cached:
        mark_provider_invoked()
        mark_provider_cached()
    with bind_provider_observation("igdb", "game") as network:
        mark_provider_invoked()
        await observe_aiohttp_headers(None, None, None)
        await observe_httpcore_trace("http2.send_request_headers.started", {})
        await observe_httpcore_trace("http2.send_request_headers.complete", {})
    assert not noop.invoked and noop.requests == 0
    assert cached.invoked and cached.cached and cached.requests == 0
    assert network.invoked and not network.cached and network.requests == 2
    assert network.request_at is not None


@pytest.mark.asyncio
async def test_no_scope_and_failure_reset():
    await observe_aiohttp_headers(None, None, None)
    mark_provider_invoked()
    with pytest.raises(RuntimeError), bind_provider_observation("igdb", "game"):
        raise RuntimeError("failed")
    assert current_provider_observation() is None


def test_retry_after_is_safe_duration_only():
    with bind_provider_observation("igdb", "game") as observation:
        observe_retry_after("120")
        observe_retry_after("secret-token")
        observe_retry_after("-1")
        observe_retry_after("999999999999999999999999")
    assert observation.retry_after_seconds == 120
    assert "secret-token" not in repr(observation)


@pytest.mark.asyncio
async def test_httpx_validation_trace_and_retry_after():
    from utils.context import create_httpx_async_client
    from utils.validation import ValidationError

    events = []

    async def prior(event, info):
        events.append(event)

    async def transport(request):
        await request.extensions["trace"]("http11.send_request_headers.started", {})
        return httpx.Response(200, headers={"Retry-After": "25"})

    async with create_httpx_async_client() as client:
        client._transport = httpx.MockTransport(transport)
        with bind_provider_observation("igdb", "game") as observation:
            await client.get("https://example.com", extensions={"trace": prior})
            with pytest.raises(ValidationError):
                await client.get("http://127.0.0.1/private")
    assert observation.requests == 1
    assert observation.retry_after_seconds == 25
    assert events == ["http11.send_request_headers.started"]


@pytest.mark.asyncio
async def test_aiohttp_redirect_and_repeated_dispatch():
    from aiohttp import web

    from utils.context import create_aiohttp_session

    calls = 0

    async def endpoint(request):
        nonlocal calls
        calls += 1
        if request.path == "/redirect":
            raise web.HTTPFound("/ok")
        return web.Response(headers={"Retry-After": "30"})

    app = web.Application()
    app.router.add_get("/{path}", endpoint)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "127.0.0.1", 0)
    await site.start()
    port = site._server.sockets[0].getsockname()[1]
    try:
        async with create_aiohttp_session() as client:
            with bind_provider_observation("steam", "game") as observation:
                for _ in range(2):
                    async with client.get(
                        f"http://127.0.0.1:{port}/redirect"
                    ) as response:
                        await response.read()
        assert observation.requests == calls == 4
        assert observation.retry_after_seconds == 30
    finally:
        await runner.cleanup()
