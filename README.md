# MCP-UI Ext-Apps Demo

Five reference [MCP-UI](https://github.com/idosal/mcp-ui) ext-apps for testing
host implementations. Each app exercises a different combination of the
MCP-UI delivery and postMessage spec — together they cover every code path a
host needs to support.

## The apps

| # | App | Resource | MIME | Hosting | Spec coverage |
|---|---|---|---|---|---|
| 1 | `show_hello` | EmbeddedResource | `text/html` | Inline | Static HTML, no scripts |
| 2 | `show_counter` | EmbeddedResource | `text/html` | Inline | JS execution, dynamic `setHeight` |
| 3 | `show_feedback` | EmbeddedResource | `text/html` | Inline | `callTool`, `sendPrompt` round-trip |
| 4 | `show_price_chart` | EmbeddedResource | `text/uri-list` | GitHub Pages | Cross-origin iframe, external CDN, live fetch |
| 5 | `show_map` | ResourceLink | `text/html` | GitHub Pages | OSM tiles, `callTool` from clicks, `openLink`, `notify` |

Plus two callback tools that prove the host's postMessage round-trip:
`submit_feedback` (called by #3) and `save_pin` (called by #5).

See [`COMPLIANCE.md`](./COMPLIANCE.md) for the per-app spec checklist.

## Live deployment

- **MCP server:** `https://mcp-ui-extapps-demo.onrender.com/mcp` (Render free tier; cold starts after idle)
- **Hosted apps:** `https://omeirhaeghe.github.io/mcp-ui-extapps-demo/` (GitHub Pages)

## Run locally

```bash
uv sync
uv run python server/server.py --port 8767
```

Server speaks Streamable HTTP at `http://localhost:8767/mcp`.

When running locally, the hosted apps (#4, #5) still load from GitHub Pages
unless you override `PUBLIC_HOSTED_BASE`:

```bash
PUBLIC_HOSTED_BASE=http://localhost:5173 uv run python server/server.py
# (and serve the hosted/ directory on :5173 separately)
```

## Test against a host

### SimpleHost

```text
/mcp add extapps-demo
> URL: https://mcp-ui-extapps-demo.onrender.com/mcp
> Auth: none
```

Then in chat:
- `call show_hello name="Alice"` → static card
- `call show_counter` → interactive counter
- `call show_feedback prompt="How was the answer?"` → form, then click submit
- `call show_price_chart symbol="ETH"` → live chart, switch 1D / 1W / 1M
- `call show_map lat=48.8566 lng=2.3522` → click map to drop pins

### Any other MCP host

The server is plain Streamable HTTP MCP — drop it into any host that supports
remote MCP servers. The five `show_*` tools each return a `ui://` resource;
a compliant host will iframe-render them.

## Repo layout

```
.
├── server/
│   ├── server.py          FastMCP server with 7 tools
│   └── apps/              Inline HTML widgets (#1-3)
├── hosted/                Static apps deployed to GH Pages (#4-5)
│   ├── 04-price-chart/
│   ├── 05-map/
│   └── _shared/host-sdk.js
├── .github/workflows/pages.yml
├── render.yaml
├── pyproject.toml
└── COMPLIANCE.md
```

## Deploying

- **GitHub Pages** auto-deploys on push to `main` whenever `hosted/**` changes
  (see `.github/workflows/pages.yml`). Enable Pages with `Source: GitHub Actions`.
- **Render** auto-deploys via `render.yaml` (Blueprint) — connect the repo
  in the Render dashboard, accept the blueprint, free tier is fine.

## License

MIT.
