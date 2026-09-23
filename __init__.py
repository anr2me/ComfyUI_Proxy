"""
ComfyUI Cloud Redirect
-----------------------
Redirects /prompt and /queue API calls to a remote "cloud GPU" ComfyUI
instance, whose URL can be set live from the Settings panel in the UI.

Drop this folder into ComfyUI/custom_nodes/ and restart ComfyUI.
"""

from server import PromptServer

from .proxy_middleware import cloud_redirect_middleware

# Registering routes has the side effect of attaching them to
# PromptServer.instance.routes, so this import must happen even though the
# module isn't otherwise referenced here.
from . import api_routes  # noqa: F401

# Must run before ComfyUI's app is frozen (i.e. before the server starts
# listening). Custom nodes load during startup, ahead of that point, so
# this is safe here.
PromptServer.instance.app.middlewares.append(cloud_redirect_middleware)

# This package adds no graph nodes, only server-side behavior.
NODE_CLASS_MAPPINGS = {}
NODE_DISPLAY_NAME_MAPPINGS = {}

WEB_DIRECTORY = "./web"

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS", "WEB_DIRECTORY"]
