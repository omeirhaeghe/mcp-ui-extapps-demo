"""MCP-UI ext-apps reference server.

Exposes 5 widget-emitting tools (one per app) plus 2 callback-receiving tools
that prove the host's postMessage round-trip end-to-end. Use this as a
compliance test bed for any MCP-UI host implementation.

    uv run python server/server.py              # :8767
    uv run python server/server.py --port 9000  # custom port

Env vars:
    PUBLIC_HOSTED_BASE   Base URL where the static apps in `hosted/` are
                         served from. Defaults to GitHub Pages for omeirhaeghe.
                         Override when self-hosting.
"""

from __future__ import annotations

import argparse
import os
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote
from uuid import uuid4

from mcp.server.fastmcp import FastMCP
from mcp.types import EmbeddedResource, ResourceLink, TextContent, TextResourceContents

mcp = FastMCP("MCP-UI Ext-Apps Demo")

APPS_DIR = Path(__file__).parent / "apps"
DEFAULT_HOSTED_BASE = "https://omeirhaeghe.github.io/mcp-ui-extapps-demo"
HOSTED_BASE = os.environ.get("PUBLIC_HOSTED_BASE", DEFAULT_HOSTED_BASE).rstrip("/")


def _load_app(name: str) -> str:
    return (APPS_DIR / name).read_text(encoding="utf-8")


def _embedded_html(uri: str, html: str) -> EmbeddedResource:
    return EmbeddedResource(
        type="resource",
        resource=TextResourceContents(
            uri=uri,
            mimeType="text/html",
            text=html,
        ),
    )


def _embedded_uri_list(uri: str, target_url: str) -> EmbeddedResource:
    """text/uri-list: the resource itself is inline, but its content is a URL
    that the host loads in the iframe via `src`. Tests the parsed-URL path."""
    return EmbeddedResource(
        type="resource",
        resource=TextResourceContents(
            uri=uri,
            mimeType="text/uri-list",
            text=target_url + "\n",
        ),
    )


def _resource_link(uri: str, mime: str = "text/html", name: str = "") -> ResourceLink:
    """resource_link: the host receives a URI directly and loads it in the
    iframe. Tests the resource_link delivery path."""
    return ResourceLink(
        type="resource_link",
        uri=uri,
        name=name or uri,
        mimeType=mime,
    )


# ---------------------------------------------------------------------------
# 1. Hello — static text/html, no JS. Simplest possible widget.
# ---------------------------------------------------------------------------

@mcp.tool()
async def show_hello(name: str = "world") -> list:
    """Render a static greeting card for the given name."""
    html = (
        _load_app("01-hello.html")
        .replace("{{NAME}}", _esc(name))
        .replace("{{TIMESTAMP}}", datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"))
    )
    uri = f"ui://hello/{uuid4().hex}"
    return [
        TextContent(type="text", text=f"Showing hello widget for {name}."),
        _embedded_html(uri, html),
    ]


# ---------------------------------------------------------------------------
# 2. Counter — interactive JS, dynamic resize.
# ---------------------------------------------------------------------------

@mcp.tool()
async def show_counter(start: int = 0) -> list:
    """Render an interactive counter starting at the given value."""
    html = _load_app("02-counter.html").replace("{{START}}", str(int(start)))
    uri = f"ui://counter/{uuid4().hex}"
    return [
        TextContent(type="text", text=f"Counter widget rendered (start={start})."),
        _embedded_html(uri, html),
    ]


# ---------------------------------------------------------------------------
# 3. Feedback — calls back to the host via callTool + sendPrompt.
# ---------------------------------------------------------------------------

@mcp.tool()
async def show_feedback(prompt: str = "How was the response?") -> list:
    """Render a feedback form. Submissions invoke the `submit_feedback` tool."""
    html = _load_app("03-feedback.html").replace("{{PROMPT}}", _esc(prompt))
    uri = f"ui://feedback/{uuid4().hex}"
    return [
        TextContent(type="text", text="Feedback widget rendered."),
        _embedded_html(uri, html),
    ]


@mcp.tool()
async def submit_feedback(rating: int, text: str = "") -> str:
    """Receive a feedback submission from the show_feedback widget.

    A spec-compliant host will invoke this when the user submits the form
    inside the widget — the round-trip proves the postMessage `tool` action
    is wired up correctly."""
    return (
        f"Received feedback: {rating}/5 stars"
        + (f' — "{text}"' if text else "")
    )


# ---------------------------------------------------------------------------
# 4. Price chart — hosted, delivered via inline text/uri-list.
# ---------------------------------------------------------------------------

@mcp.tool()
async def show_price_chart(symbol: str = "BTC") -> list:
    """Render a live crypto price chart (BTC/ETH/SOL/DOGE/ADA)."""
    sym = (symbol or "BTC").upper()
    target = f"{HOSTED_BASE}/04-price-chart/?symbol={quote(sym)}"
    uri = f"ui://price-chart/{uuid4().hex}"
    return [
        TextContent(type="text", text=f"Price chart for {sym} rendered."),
        _embedded_uri_list(uri, target),
    ]


# ---------------------------------------------------------------------------
# 5. Map — hosted, delivered via resource_link (separate spec path).
# ---------------------------------------------------------------------------

@mcp.tool()
async def show_map(lat: float = 37.7749, lng: float = -122.4194) -> list:
    """Render an interactive map. Pin drops invoke the `save_pin` tool."""
    target = f"{HOSTED_BASE}/05-map/?lat={lat}&lng={lng}"
    return [
        TextContent(type="text", text=f"Map rendered centered at {lat}, {lng}."),
        _resource_link(target, mime="text/html", name="Interactive map"),
    ]


@mcp.tool()
async def save_pin(lat: float, lng: float, label: str = "") -> str:
    """Receive a pin drop from the show_map widget."""
    return (
        f"Saved pin at ({lat:.4f}, {lng:.4f})"
        + (f' as "{label}"' if label else "")
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _esc(s: str) -> str:
    return (
        str(s)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#39;")
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="MCP-UI ext-apps demo server")
    parser.add_argument("--port", type=int, default=int(os.environ.get("PORT", 8767)))
    parser.add_argument("--host", default="0.0.0.0")
    args = parser.parse_args()

    mcp.run(transport="streamable-http", host=args.host, port=args.port)
