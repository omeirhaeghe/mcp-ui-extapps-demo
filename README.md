# MCP Apps Demo Server

A reference [MCP Apps](https://github.com/modelcontextprotocol/ext-apps) server you
can deploy in one click — twenty-five interactive widgets that exercise every part
of the spec. Use it to test your own MCP host, prototype your own widgets, or play
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

All twenty-five are spec-compliant: each tool declares `_meta.ui.resourceUri`, the
matching resource is registered with `text/html;profile=mcp-app`, and the
client-side JS uses the official [`@modelcontextprotocol/ext-apps`](https://www.npmjs.com/package/@modelcontextprotocol/ext-apps) SDK.

Each row names the SEP-1865 surfaces the widget exercises. Brackets give the
spec section / method ID so you can grep [the spec](https://modelcontextprotocol.io/community/seps/1865-mcp-apps-interactive-user-interfaces-for-mcp).

| # | Tool | What it shows | SEP-1865 surface tested |
|---|---|---|---|
| 1  | `show_hello`            | Static greeting card                                | `text/html;profile=mcp-app` resource + `_meta.ui.resourceUri` on tool + `ui/initialize` handshake (bare minimum) |
| 2  | `show_counter`          | +1 / −1 buttons, "Grow" panel                       | `ui/notifications/tool-input` (read tool args) + `ui/notifications/size-changed` (SDK auto-resize) |
| 3  | `show_feedback`         | Star rating + comments form                         | `tools/call` host→app (`submit_feedback`) + `ui/message` (post user message into chat) |
| 4  | `show_price_chart`      | Live BTC/ETH/SOL/DOGE/ADA chart                     | `_meta.ui.csp.resourceDomains` (Chart.js CDN) + `_meta.ui.csp.connectDomains` (CoinGecko `fetch`) + `ui/open-link` |
| 5  | `show_map`              | Click-to-drop-pin map                               | `_meta.ui.csp.resourceDomains` (Leaflet + OSM tile servers) + `tools/call` (`save_pin`) + `ui/open-link` |
| 6  | `show_tictactoe`        | Tic-tac-toe vs server-side minimax                  | `tools/call` with `outputSchema` / `structuredContent` round-trip per move |
| 7  | `show_drawing`          | Canvas drawing pad with brush + colors              | Large-payload `tools/call` (PNG data URL via `save_drawing`) — stresses message-channel size limits |
| 8  | `show_todos`            | Todo list with add / toggle / delete                | Multiple `tools/call` round-trips per session (`add_todo` / `toggle_todo` / `delete_todo`) |
| 9  | `show_weather`          | Current conditions for any city                     | `_meta.ui.csp.connectDomains` against a second external API (Open-Meteo, no auth) |
| 10 | `show_3d`               | Rotating 3D cube / sphere / torus / knot            | `_meta.ui.csp.resourceDomains` (three.js CDN) + WebGL inside the sandbox |
| 11 | `show_punch_monkey`     | 15-second clicker mini-game                         | High-frequency local state, single end-of-round `tools/call` (`record_punch_score`) — verifies the host doesn't drop late callbacks |
| 12 | `show_adventure`        | Branching Apple-II-style mystery                    | Split UX: scene rendered in widget via `tools/call`, user answers typed into chat → model interprets → next `tools/call` |
| 13 | `show_hover`            | Spotlight that follows the cursor over hidden words | Pure pointer-event widget — verifies the iframe receives `mousemove`/`mouseenter`/`mouseleave` (no clicks, no callbacks) |
| 14 | `show_florida_man`      | Frogger-style crossing dodging golf carts 🤠🛺🐊      | Canvas + `requestAnimationFrame` + keyboard input inside the sandbox; end-of-round `tools/call` (`record_florida_score`) |
| 15 | `show_kanban`           | Kanban board with Maximize button                   | `availableDisplayModes` app capability + `ui/request-display-mode` (view→host) + `ui/notifications/host-context-changed` (host→view) |
| 16 | `show_themed_swatches`  | Live grid of host design tokens                     | `ui/notifications/host-context-changed` reactivity over `HostContext.styles.variables.*` (CSS design tokens) |
| 17 | `show_signature`        | Signature pad with native PNG download              | `ui/download-file` with an inline `EmbeddedResource` (`image/png` blob) — no callback round-trip |
| 18 | `show_one_shot`         | Self-dismissing 1-question survey                   | `ui/notifications/request-teardown` (view→host) + `ui/resource-teardown` (host→view) cleanup hook |
| 19 | `show_internal_counter` | Counter with model-hidden +1 callback               | `_meta.ui.visibility: ["app"]` — `bump_counter` is callable from the iframe but absent from the model's `tools/list` |
| 20 | `show_url`              | Wraps an arbitrary URL as an MCP-app via nested iframe | `_meta.ui.csp.frameDomains` (CSP `frame-src`) — surfaces both CSP-block and `X-Frame-Options: DENY` failure modes |
| 21 | `show_user_profile`     | Preferences form (name / units / reply style)       | `ui/update-model-context` (view→host) — pushes context blocks into the model with no `tools/call` round-trip |
| 23 | `show_product_carousel` | Snap-scrolling carousel with Unsplash photos + embedded checkout modal | `tools/call` (`add_to_cart`, `checkout`) + `_meta.ui.csp.resourceDomains` (Unsplash CDN) — also a CSS playground (gradient borders, shine sweep, lift-on-hover) |
| 24 | `show_age_picker`       | iOS-style wheel + manual input with life-stage chip | `tools/call` (`submit_age`) + `ui/notifications/tool-input` (initial age) — visual demo with morphing gradient theme |
| 25 | `show_age_gate`         | Neutral FTC-style DOB gate, jurisdiction-aware (COPPA / GDPR / LGPD / DPDP / PIPA), persistent decision | `tools/call` (`submit_age_check`) — data-minimization pattern: DOB stays client-side, only the derived decision crosses the boundary |
| 26 | `show_taboola_news`     | Taboola-style news grid — hero card, "Sponsored" badges, "Recommended by TABOOLA" footer, live category picker (general / business / tech / science / health / sports / entertainment), liquid-glass styling | Real keyed external API (NewsAPI) proxied **server-side** via `NEWSAPI_KEY` env var + structured result **inlined into the resource HTML** at `resources/read` time (works around hosts that route widget→server tool results to chat instead of back to the iframe) + `ui/open-link` |

Plus the callback tools the widgets invoke: `submit_feedback`, `save_pin`,
`make_move`, `save_drawing`, `add_todo`, `toggle_todo`, `delete_todo`,
`record_punch_score`, `advance_adventure`, `record_florida_score`,
`submit_survey`, `bump_counter` (app-only), `add_to_cart`, `checkout`,
`submit_age`, `submit_age_check`.

---

## Spec coverage analysis

> **TL;DR** — All 25 are spec-compliant, but several test the same SEP-1865
> surface from a different angle. If your goal is *minimum-redundant*
> coverage of the spec (rather than a varied gallery), the breakdown below
> shows which widgets you can drop without losing any surface.

<details>
<summary><b>Which widgets test which spec surface</b> (click to expand)</summary>

#### Surfaces tested by exactly one widget — keep all of these

| Spec surface | Tested by |
|---|---|
| `text/html;profile=mcp-app` + `_meta.ui.resourceUri` + `ui/initialize` (bare-minimum static render) | #1 `show_hello` |
| `ui/notifications/size-changed` (auto-resize) | #2 `show_counter` |
| `ui/message` (post user message into chat) | #3 `show_feedback` |
| `tools/call` with `outputSchema` / `structuredContent` | #6 `show_tictactoe` |
| Large-payload `tools/call` (message-channel size limits) | #7 `show_drawing` |
| Same `_meta.ui.resourceUri` shared by multiple tools (the second tool *updates* the existing widget) | #12 `show_adventure` |
| `availableDisplayModes` + `ui/request-display-mode` + `host-context-changed` (`displayMode` field) | #15 `show_kanban` |
| `host-context-changed` reactivity over `styles.variables.*` (theme tokens) | #16 `show_themed_swatches` |
| `ui/download-file` with embedded blob | #17 `show_signature` |
| `ui/notifications/request-teardown` + `ui/resource-teardown` | #18 `show_one_shot` |
| `_meta.ui.visibility: ["app"]` (model-hidden tool) | #19 `show_internal_counter` |
| `_meta.ui.csp.frameDomains` (CSP `frame-src` for nested iframes) | #20 `show_url` |
| `ui/update-model-context` (view→host context push) | #21 `show_user_profile` |

#### Surfaces tested by multiple widgets

| Spec surface | Tested by | Verdict |
|---|---|---|
| `tools/call` (host→app proxy) | #3, #5, #6, #7, #8, #11, #12, #14, #18, #19 | most fully redundant; #6 (`outputSchema`) and #7 (large payload) add real angles |
| `_meta.ui.csp.resourceDomains` (CSP `script-src`) | #4 (Chart.js), #5 (Leaflet), #10 (three.js) | #10 adds nothing #4/#5 don't already prove |
| `_meta.ui.csp.connectDomains` (CSP `connect-src`) | #4 (CoinGecko), #9 (Open-Meteo) | one external API is enough |
| `ui/open-link` | #4, #5 | minor overlap |
| `host-context-changed` | #15 (`displayMode`), #16 (`theme` + `styles.variables`) | **soft** — different fields; hosts often propagate one and not the other, so both stay useful |
| Cross-origin `<img>` loading inside the sandbox | #5 (OSM tiles), #4 (Chart.js fonts) | **soft** — distinct CSP directive (`img-src`) |
| Canvas + `requestAnimationFrame` inside the sandbox | #11, #14 | not a spec surface (gated by `allow-scripts`); pick one |

#### Drop candidates (spec-redundant)

| # | Widget | Why redundant |
|---|---|---|
| 8  | `show_todos`        | Adds no new spec surface — just more `tools/call`s. Already covered by #3, #5, #6 |
| 9  | `show_weather`      | Same `csp.connectDomains` story as #4, just a different API host |
| 10 | `show_3d`           | Same `csp.resourceDomains` story as #4/#5; WebGL itself isn't a spec surface |
| 11 | `show_punch_monkey` | Spec-wise = #3 (`tools/call`); "high-frequency state" is not a host-side surface |
| 13 | `show_hover`        | Pointer events propagating to a sandboxed iframe isn't a distinct spec surface — `allow-scripts` covers it |
| 14 | `show_florida_man`  | Same as #11 spec-wise; keyboard delivery isn't a separate spec surface |

> Keep one of {#11, #14} if you want a representative "stresses local
> state + late callback" demo. The others can go without losing any
> spec coverage.

#### Minimal complete-coverage set (13 widgets)

If you cut hard: **#1, #2, #3, #4, #5, #6, #7, #12, #15, #16, #17, #18, #19, #20, #21**
(plus optionally one of #11/#14). That hits every SEP-1865 surface this
repo currently exercises, with no two widgets covering the same surface.

#### Surfaces still uncovered (no widget tests these)

Pruning won't fix these — only adding new widgets will:

- `_meta.ui.csp.baseUriDomains`
- `_meta.ui.permissions.{camera, microphone, geolocation, clipboardWrite}`
- `_meta.ui.domain` (custom origin)
- `pip` display mode (only `inline` / `fullscreen` are exercised in #15)
- `ui/notifications/tool-input-partial` / `tool-cancelled`
- `notifications/tools/list_changed` / `resources/list_changed`
- `sampling` host capability (`createSamplingMessage`)
- `containerDimensions`, `safeAreaInsets`, `deviceCapabilities` from `HostContext`

</details>

---

## Quick deploy on Render

1. Click the **Deploy to Render** button above (or fork → connect in Render).
2. Accept the `render.yaml` blueprint. Free tier is fine.
3. Wait ~2 min for the first build.
4. Add the URL to your MCP host: `https://<your-service>.onrender.com/mcp`.

That's it for 24 of 25 widgets — no auth, no DB. The one exception is
**#26 `show_taboola_news`**, which hits NewsAPI server-side and needs
its key in an env var:

- Grab a free key at <https://newsapi.org/register> (no credit card,
  100 reqs/day — enough for ~14 widget mounts).
- In the Render dashboard for your service: **Environment → Add
  Environment Variable** → `NEWSAPI_KEY` = `<your-key>`.

The variable is declared in `render.yaml` with `sync: false` so it
must be set in the dashboard, not committed.

## Run locally

Requires Python 3.11+ and [`uv`](https://docs.astral.sh/uv/).

```bash
uv sync
uv run python server/server.py --port 8767
```

The server speaks Streamable HTTP at `http://localhost:8767/mcp`.

For `show_taboola_news`, drop `NEWSAPI_KEY=…` into a `.env` file at the
repo root (already in `.gitignore`); the server auto-loads it on
startup. Or export it inline: `NEWSAPI_KEY=… uv run python server/server.py`.

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
│  ─ 25 ui://… resources, mime "text/html;profile=mcp-app"         │
│  ─ 25 widget-emitting tools with _meta.ui.resourceUri            │
│  ─ N callback tools (save_pin, make_move, save_drawing, …)       │
└──────────────────────────────────────────────────────────────────┘
```

## Repo layout

```
.
├── server/
│   ├── server.py          FastMCP server, 20 widgets + callbacks
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


