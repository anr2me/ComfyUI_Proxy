"""
Registers GET/POST /cloud_redirect/config on ComfyUI's own PromptServer so
the frontend can read and update the cloud GPU URL. These two routes are
never proxied (they're not in REDIRECTED_PATHS).
"""

from aiohttp import web
from server import PromptServer

from .cloud_state import get_cloud_url, set_cloud_url

routes = PromptServer.instance.routes


@routes.get("/cloud_redirect/config")
async def get_config(request: web.Request) -> web.Response:
    return web.json_response({"cloud_url": get_cloud_url()})


@routes.post("/cloud_redirect/config")
async def set_config(request: web.Request) -> web.Response:
    try:
        data = await request.json()
    except Exception:
        return web.json_response({"error": "Expected JSON body"}, status=400)

    set_cloud_url(data.get("cloud_url", ""))
    return web.json_response({"cloud_url": get_cloud_url()})
