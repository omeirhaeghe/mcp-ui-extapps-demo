"""MCP Apps (SEP-1865) reference server.

Five widget-emitting tools (one per app) plus two callback tools that prove
the host's JSON-RPC-over-postMessage round-trip works end-to-end. Use this
as a compliance test bed for any MCP Apps host implementation.

    uv run python server/server.py              # :8767
    uv run python server/server.py --port 9000  # custom port
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path

import uvicorn
from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings
from starlette.middleware.cors import CORSMiddleware

mcp = FastMCP(
    "Toto",
    transport_security=TransportSecuritySettings(enable_dns_rebinding_protection=False),
)

APPS_DIR = Path(__file__).parent / "apps"


def _load_app(name: str) -> str:
    return (APPS_DIR / name).read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# 1. Hello — static text/html, no JS beyond protocol shim.
# ---------------------------------------------------------------------------

@mcp.resource(
    "ui://hello",
    mime_type="text/html;profile=mcp-app",
    meta={"ui": {"prefersBorder": True}},
)
def hello_app() -> str:
    return _load_app("01-hello.html")


@mcp.tool(meta={"ui": {"resourceUri": "ui://hello"}})
async def show_hello(name: str = "world") -> str:
    """Render a static greeting card for the given name."""
    return f"Showing hello widget for {name}."


# ---------------------------------------------------------------------------
# 2. Counter — JS execution + dynamic resize via ui/notifications/size-changed.
# ---------------------------------------------------------------------------

@mcp.resource(
    "ui://counter",
    mime_type="text/html;profile=mcp-app",
    meta={"ui": {"prefersBorder": True}},
)
def counter_app() -> str:
    return _load_app("02-counter.html")


@mcp.tool(meta={"ui": {"resourceUri": "ui://counter"}})
async def show_counter(start: int = 0) -> str:
    """Render an interactive counter starting at the given value."""
    return f"Counter widget rendered (start={start})."


# ---------------------------------------------------------------------------
# 3. Feedback — tools/call + ui/message round-trip.
# ---------------------------------------------------------------------------

@mcp.resource(
    "ui://feedback",
    mime_type="text/html;profile=mcp-app",
    meta={"ui": {"prefersBorder": True}},
)
def feedback_app() -> str:
    return _load_app("03-feedback.html")


@mcp.tool(meta={"ui": {"resourceUri": "ui://feedback"}})
async def show_feedback(prompt: str = "How was the response?") -> str:
    """Render a feedback form. Submissions invoke the `submit_feedback` tool."""
    return "Feedback widget rendered."


@mcp.tool()
async def submit_feedback(rating: int, text: str = "") -> str:
    """Receive a feedback submission from the show_feedback widget."""
    return (
        f"Received feedback: {rating}/5 stars"
        + (f' — "{text}"' if text else "")
    )


# ---------------------------------------------------------------------------
# 4. Price chart — external CDN script + cross-origin fetch.
# ---------------------------------------------------------------------------

@mcp.resource(
    "ui://price-chart",
    mime_type="text/html;profile=mcp-app",
    meta={
        "ui": {
            "prefersBorder": True,
            "csp": {
                "resourceDomains": ["https://cdn.jsdelivr.net"],
                "connectDomains": ["https://api.coingecko.com"],
            },
        }
    },
)
def price_chart_app() -> str:
    return _load_app("04-price-chart.html")


@mcp.tool(meta={"ui": {"resourceUri": "ui://price-chart"}})
async def show_price_chart(symbol: str = "BTC") -> str:
    """Render a live crypto price chart (BTC/ETH/SOL/DOGE/ADA)."""
    return f"Price chart for {(symbol or 'BTC').upper()} rendered."


# ---------------------------------------------------------------------------
# 5. Map — multi-callback (tools/call + ui/open-link).
# ---------------------------------------------------------------------------

@mcp.resource(
    "ui://map",
    mime_type="text/html;profile=mcp-app",
    meta={
        "ui": {
            "prefersBorder": True,
            "csp": {
                "resourceDomains": [
                    "https://unpkg.com",
                    "https://tile.openstreetmap.org",
                ],
            },
        }
    },
)
def map_app() -> str:
    return _load_app("05-map.html")


@mcp.tool(meta={"ui": {"resourceUri": "ui://map"}})
async def show_map(lat: float = 37.7749, lng: float = -122.4194) -> str:
    """Render an interactive map. Pin drops invoke the `save_pin` tool."""
    return f"Map rendered centered at {lat}, {lng}."


@mcp.tool()
async def save_pin(lat: float, lng: float, label: str = "") -> str:
    """Receive a pin drop from the show_map widget."""
    return (
        f"Saved pin at ({lat:.4f}, {lng:.4f})"
        + (f' as "{label}"' if label else "")
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="MCP Apps demo server")
    parser.add_argument("--port", type=int, default=int(os.environ.get("PORT", 8767)))
    parser.add_argument("--host", default="0.0.0.0")
    args = parser.parse_args()

    mcp.settings.host = args.host
    mcp.settings.port = args.port

    app = mcp.streamable_http_app()
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
        allow_headers=["*"],
        expose_headers=["mcp-session-id"],
    )
    uvicorn.run(app, host=args.host, port=args.port)
