"""
aiohttp middleware that, for a configurable set of API paths, forwards the
incoming request to a remote "cloud GPU" ComfyUI instance instead of letting
this instance's own route handlers process it.

Registered as the outermost middleware in __init__.py so it runs before
ComfyUI's own route handlers.
"""

import asyncio
import logging

import aiohttp
from aiohttp import web

from .cloud_state import get_cloud_url

logger = logging.getLogger("comfyui_cloud_redirect")

# Plain request/response paths that get forwarded to the cloud GPU when a
# URL is configured. Matching is exact-or-prefix (see _matches), so
# "/history" also covers "/history/{prompt_id}".
HTTP_REDIRECTED_PATHS = {
    "/prompt",
    "/queue",
    "/history",
    "/view",
    "/viewvideo",
    "/interrupt",
    "/api/jobs",
    "/internal/logs",
}

# Paths that are websocket upgrades rather than plain HTTP and need message
# pumping instead of a single request/response proxy.
WS_REDIRECTED_PATHS = {"/ws"}

# Headers that must not be blindly forwarded either direction.
_HOP_BY_HOP = {
    "host",
    "content-length",
    "content-encoding",
    "transfer-encoding",
    "connection",
}


def _matches(path: str, path_set: set) -> bool:
    return any(path == p or path.startswith(p + "/") for p in path_set)


@web.middleware
async def cloud_redirect_middleware(request: web.Request, handler):
    cloud_url = get_cloud_url()
    if not cloud_url:
        return await handler(request)

    path = request.path

    if _matches(path, WS_REDIRECTED_PATHS) and _is_ws_upgrade(request):
        return await _proxy_websocket(request, cloud_url)

    if _matches(path, HTTP_REDIRECTED_PATHS):
        return await _proxy_request(request, cloud_url)

    return await handler(request)


def _is_ws_upgrade(request: web.Request) -> bool:
    return request.headers.get("Upgrade", "").lower() == "websocket"


async def _proxy_request(request: web.Request, cloud_url: str) -> web.StreamResponse:
    target_url = f"{cloud_url}{request.path}"
    if request.query_string:
        target_url += f"?{request.query_string}"

    body = await request.read()
    forward_headers = {
        k: v for k, v in request.headers.items() if k.lower() not in _HOP_BY_HOP
    }

    logger.info("Redirecting %s %s -> %s", request.method, request.path, target_url)

    try:
        async with aiohttp.ClientSession() as session:
            async with session.request(
                request.method,
                target_url,
                headers=forward_headers,
                data=body or None,
                allow_redirects=False,
            ) as resp:
                resp_body = await resp.read()
                resp_headers = {
                    k: v
                    for k, v in resp.headers.items()
                    if k.lower() not in _HOP_BY_HOP
                }
                return web.Response(
                    body=resp_body, status=resp.status, headers=resp_headers
                )
    except aiohttp.ClientError as e:
        logger.error("Failed to reach cloud GPU at %s: %s", cloud_url, e)
        return web.json_response(
            {"error": f"Failed to reach cloud GPU at {cloud_url}: {e}"},
            status=502,
        )


async def _proxy_websocket(request: web.Request, cloud_url: str) -> web.WebSocketResponse:
    """Proxies a websocket connection (e.g. ComfyUI's /ws progress/preview
    channel) by opening a matching connection to the cloud GPU and pumping
    messages in both directions until either side disconnects."""
    ws_server = web.WebSocketResponse()
    await ws_server.prepare(request)

    ws_scheme = "wss" if cloud_url.startswith("https") else "ws"
    host_and_rest = cloud_url.split("://", 1)[-1]
    target_url = f"{ws_scheme}://{host_and_rest}{request.path}"
    if request.query_string:
        target_url += f"?{request.query_string}"

    logger.info("Proxying websocket %s -> %s", request.path, target_url)

    try:
        async with aiohttp.ClientSession() as session:
            async with session.ws_connect(target_url, max_msg_size=0) as ws_client:

                async def pump(src, dst):
                    async for msg in src:
                        if msg.type == aiohttp.WSMsgType.TEXT:
                            await dst.send_str(msg.data)
                        elif msg.type == aiohttp.WSMsgType.BINARY:
                            await dst.send_bytes(msg.data)
                        elif msg.type in (
                            aiohttp.WSMsgType.ERROR,
                            aiohttp.WSMsgType.CLOSE,
                            aiohttp.WSMsgType.CLOSING,
                            aiohttp.WSMsgType.CLOSED,
                        ):
                            break

                await asyncio.gather(
                    pump(ws_server, ws_client),
                    pump(ws_client, ws_server),
                    return_exceptions=True,
                )
    except aiohttp.ClientError as e:
        logger.error("Failed to reach cloud GPU websocket at %s: %s", target_url, e)
        if not ws_server.closed:
            await ws_server.close(code=1011, message=str(e).encode())

    return ws_server
