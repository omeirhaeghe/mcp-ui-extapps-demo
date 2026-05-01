# MCP Apps Demo Server

A reference [MCP Apps](https://github.com/modelcontextprotocol/ext-apps) server you
can deploy in one click — fourteen interactive widgets that exercise every part of
the spec. Use it to test your own MCP host, prototype your own widgets, or play
with the protocol.

> **What is MCP Apps?**
> [SEP-1865 — *MCP Apps: Interactive User Interfaces for MCP*](https://modelcontextprotocol.io/community/seps/1865-mcp-apps-interactive-user-interfaces-for-mcp)
> is the open standard for embedding interactive widgets in chat clients. An MCP
> server registers `ui://` resources with `mimeType: text/html;profile=mcp-app`,
> and a host (Claude, ChatGPT, Goose, VS Code, …) renders them in an iframe with
> a JSON-RPC bridge to the model. This repo is a plug-and-play reference server
> for the spec.

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/omeirhaeghe/mcp-ui-extapps-demo)

**Live demo:** `https://mcp-ui-extapps-demo.onrender.com/mcp` (Render free tier — cold-starts after idle).

---

## The widgets

All fourteen are spec-compliant: each tool declares `_meta.ui.resourceUri`, the
matching resource is registered with `text/html;profile=mcp-app`, and the
client-side JS uses the official [`@modelcontextprotocol/ext-apps`](https://www.npmjs.com/package/@modelcontextprotocol/ext-apps) SDK.

| # | Tool | What it shows | Spec surface tested |
|---|---|---|---|
| 1 | `show_hello` | Static greeting card | Bare-minimum widget — static HTML, init handshake |
| 2 | `show_counter` | +1 / −1 buttons, "Grow" panel | JS interactivity + the SDK's `ResizeObserver` auto-resize |
| 3 | `show_feedback` | Star rating + comments form | `callServerTool` (`submit_feedback`) + `sendMessage` round-trip |
| 4 | `show_price_chart` | Live BTC/ETH/SOL/DOGE/ADA chart | External CDN script (Chart.js) + cross-origin `fetch` (CoinGecko) |
| 5 | `show_map` | Click-to-drop-pin map | OSM tiles + Leaflet + `callServerTool` (`save_pin`) + `openLink` |
| 6 | `show_tictactoe` | Tic-tac-toe vs server-side minimax | Per-move `callServerTool` round-trip with `structuredContent` |
| 7 | `show_drawing` | Canvas drawing pad with brush + colors | Large-payload `callServerTool` (`save_drawing` with PNG data URL) |
| 8 | `show_todos` | Todo list with add / toggle / delete | Multiple `callServerTool` round-trips per session |
| 9 | `show_weather` | Current conditions for any city | Different external API (Open-Meteo, no auth) |
| 10 | `show_3d` | Rotating 3D cube / sphere / torus / knot | three.js + WebGL via CDN |
| 11 | `show_punch_monkey` | 15-second clicker mini-game | High-frequency client-side state, end-of-round score callback |
| 12 | `show_adventure` | Branching Apple-II-style mystery | Picture-in-widget, answers-in-chat — model orchestrates the story |
| 13 | `show_hover` | Spotlight that follows the cursor over hidden words | Pure-hover interaction — `mousemove` / `mouseenter` / `mouseleave`, no clicks |
| 14 | `show_florida_man` | Frogger-style crossing dodging golf carts 🤠🛺🐊 | Canvas + `requestAnimationFrame` game loop, keyboard + on-screen D-pad |

Plus the callback tools the widgets invoke: `submit_feedback`, `save_pin`,
`make_move`, `save_drawing`, `add_todo`, `toggle_todo`, `delete_todo`,
`record_punch_score`, `advance_adventure`, `record_florida_score`.

---

## Quick deploy on Render

1. Click the **Deploy to Render** button above (or fork → connect in Render).
2. Accept the `render.yaml` blueprint. Free tier is fine.
3. Wait ~2 min for the first build.
4. Add the URL to your MCP host: `https://<your-service>.onrender.com/mcp`.

That's it. No env vars, no auth, no DB.

## Run locally

Requires Python 3.11+ and [`uv`](https://docs.astral.sh/uv/).

```bash
uv sync
uv run python server/server.py --port 8767
```

The server speaks Streamable HTTP at `http://localhost:8767/mcp`.

Test against the [reference `basic-host`](https://github.com/modelcontextprotocol/ext-apps/tree/main/examples/basic-host):

```bash
git clone https://github.com/modelcontextprotocol/ext-apps && cd ext-apps
npm install && npm run build
SERVERS='["http://localhost:8767/mcp"]' npm run start --prefix examples/basic-host
# open http://localhost:8080
```

## Connect from a host

### Claude.ai / Claude Desktop

Settings → Connectors → **Add custom connector** → paste the `/mcp` URL.

### Any MCP-compliant host

The server is plain Streamable HTTP. The handshake sequence is the standard MCP
one (`initialize` → `notifications/initialized`), and every widget-emitting tool
declares `_meta.ui.resourceUri` so spec-aware hosts know to render the widget.

---

## Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│  Host (Claude, ChatGPT, Goose, custom MCP host…)                │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │  iframe (sandboxed)                                        │  │
│  │  ┌──────────────────────────────────────────────────────┐  │  │
│  │  │  Widget HTML (served from ui://… resource)           │  │  │
│  │  │  imports @modelcontextprotocol/ext-apps from CDN      │  │  │
│  │  │  app.callServerTool(...) → tools/call (JSON-RPC)      │  │  │
│  │  └──────────────────────────────────────────────────────┘  │  │
│  └────────────────────────────────────────────────────────────┘  │
│                              ▲                                   │
│            JSON-RPC over postMessage (SEP-1865)                  │
│                              ▼                                   │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │  MCP client                                                │  │
│  └────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────┘
                               ▲
                Streamable HTTP MCP transport
                               ▼
┌──────────────────────────────────────────────────────────────────┐
│  This server (Python, FastMCP)                                   │
│  ─ 14 ui://… resources, mime "text/html;profile=mcp-app"         │
│  ─ 14 widget-emitting tools with _meta.ui.resourceUri            │
│  ─ N callback tools (save_pin, make_move, save_drawing, …)       │
└──────────────────────────────────────────────────────────────────┘
```

## Repo layout

```
.
├── server/
│   ├── server.py          FastMCP server, 14 widgets + callbacks
│   └── apps/              Self-contained widget HTML (one file each)
├── render.yaml            Render blueprint (one-click deploy)
├── pyproject.toml         uv / pip dependencies
└── COMPLIANCE.md          Per-widget spec coverage checklist
```

## Adding your own widget

1. Drop a self-contained HTML file in `server/apps/` that imports the SDK:
   ```html
   <script type="module">
     import { App } from "https://cdn.jsdelivr.net/npm/@modelcontextprotocol/ext-apps@1.7.1/dist/src/app-with-deps.js";
     const app = new App({ name: "my-widget", version: "1.0.0" });
     app.ontoolinput = (params) => { /* read params.arguments here */ };
     app.connect();
   </script>
   ```
2. In `server.py`, register the resource and a tool that points at it:
   ```python
   @mcp.resource(
       "ui://my-widget",
       mime_type="text/html;profile=mcp-app",
       meta={"ui": {"prefersBorder": True, "csp": _SDK_CSP}},
   )
   def my_widget_app() -> str:
       return _load_app("my-widget.html")

   @mcp.tool(meta={"ui": {"resourceUri": "ui://my-widget"}})
   async def show_my_widget() -> str:
       return "Rendered."
   ```
3. Push to `main` — Render auto-redeploys.

If your widget needs external scripts or APIs, add them to the resource's
`csp.resourceDomains` / `csp.connectDomains`.

## Compliance

Validated against [SEP-1865 (draft)](https://github.com/modelcontextprotocol/ext-apps/blob/main/specification/draft/apps.mdx)
and the official [`@modelcontextprotocol/ext-apps`](https://github.com/modelcontextprotocol/ext-apps) SDK (v1.7.1).
See [`COMPLIANCE.md`](./COMPLIANCE.md) for the per-widget checklist.

## License

MIT. Have fun.

---


