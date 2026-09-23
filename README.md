# ComfyUI Proxy

Redirects some ComfyUI's API calls of a local ComfyUI instance
to a remote "cloud GPU" ComfyUI instance. The remote URL is stored server-side,
editable live from ComfyUI's **Settings** panel (gear icon → "Cloud GPU URL"),
and persisted to `cloud_config.json` so it survives restarts.

## Install

1. Clone/copy this repository into `ComfyUI/custom_nodes/`, e.g.:
   ```
   ComfyUI/custom_nodes/ComfyUI_Proxy/
   ```
2. Restart ComfyUI.
3. Open Settings → "Cloud GPU URL" → enter something like
   `https://my-cloud-gpu.example.com` (no trailing slash needed).

Once set, requests to any of the following get forwarded to that URL, and
the remote's response (or, for `/ws`, its message stream) is relayed back as
if it came from the local server. Leave the field empty to process
everything locally again.

- `/prompt`, `/queue` — submit jobs, inspect/clear the queue
- `/history` (and `/history/{prompt_id}`) — completed job results
- `/view`, `/viewvideo` — fetching generated images/videos
- `/interrupt` — cancel the running job
- `/api/jobs`, `/internal/logs` — forwarded as-is if you have matching
  endpoints locally/remotely; these aren't part of stock ComfyUI, so nothing
  registers them on the local server if you don't have your own routes for
  them — the middleware will just proxy the request through
- `/ws` — the websocket used for execution progress and live previews,
  proxied by pumping messages in both directions rather than a single
  request/response

## How it works

- `cloud_state.py` holds the URL in memory and mirrors it to
  `cloud_config.json`.
- `proxy_middleware.py` is an aiohttp middleware, inserted as the first
  middleware on ComfyUI's `web.Application`. Each incoming request's path is
  checked (exact match, or as a prefix like `/history/abc123`) against
  `HTTP_REDIRECTED_PATHS` for a plain proxy, or `WS_REDIRECTED_PATHS` for a
  websocket upgrade. If it matches and a cloud URL is set, the request is
  proxied instead of letting ComfyUI's own handler run.
- `api_routes.py` adds `GET`/`POST /cloud_redirect/config` for reading and
  writing the URL. These are not in the redirected path sets, so they always
  run locally.
- `web/cloud_redirect.js` adds the Settings-panel field, which reads the
  current value on load and POSTs changes back to `/cloud_redirect/config`.

## Caveats

- `/prompt`, `/queue`, `/history`, `/view`, `/viewvideo`, and `/interrupt`
  are proxied by fully buffering the response in memory before returning it
  — fine for JSON and typical images, but worth knowing if you're viewing
  very large videos.
- Anything not in `HTTP_REDIRECTED_PATHS`/`WS_REDIRECTED_PATHS` (e.g.
  `/upload/image`, `/object_info`) still runs locally. Add more paths to
  those sets in `proxy_middleware.py` if you need them redirected too.

## Security note

`/cloud_redirect/config` has no auth check — anyone who can reach your
ComfyUI server's HTTP API can read or change the cloud GPU URL. Fine for
local/trusted use; if you expose ComfyUI publicly, put it behind your own
auth/reverse proxy.
