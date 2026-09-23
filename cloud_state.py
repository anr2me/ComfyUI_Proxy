"""
Stores the "cloud GPU" base URL that /prompt and /queue requests get
redirected to. Persisted to a small JSON file next to this module so the
value survives a ComfyUI restart.
"""

import json
import os
import threading

_CONFIG_PATH = os.path.join(os.path.dirname(__file__), "cloud_config.json")
_lock = threading.Lock()
_cloud_url = ""


def _load() -> None:
    global _cloud_url
    if os.path.exists(_CONFIG_PATH):
        try:
            with open(_CONFIG_PATH, "r") as f:
                data = json.load(f)
                _cloud_url = data.get("cloud_url", "")
        except (json.JSONDecodeError, OSError):
            _cloud_url = ""


def _save() -> None:
    with open(_CONFIG_PATH, "w") as f:
        json.dump({"cloud_url": _cloud_url}, f)


_load()


def get_cloud_url() -> str:
    """Returns the currently configured cloud GPU base URL, or "" if unset
    (meaning: run locally, don't redirect)."""
    with _lock:
        return _cloud_url


def set_cloud_url(url: str) -> None:
    """Updates the cloud GPU base URL and persists it to disk."""
    global _cloud_url
    with _lock:
        _cloud_url = (url or "").strip().rstrip("/")
        _save()
