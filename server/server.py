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

_SDK_CSP = {"resourceDomains": ["https://cdn.jsdelivr.net"]}


@mcp.resource(
    "ui://hello",
    mime_type="text/html;profile=mcp-app",
    meta={"ui": {"prefersBorder": True, "csp": _SDK_CSP}},
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
    meta={"ui": {"prefersBorder": True, "csp": _SDK_CSP}},
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
    meta={"ui": {"prefersBorder": True, "csp": _SDK_CSP}},
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
    # cdn.jsdelivr.net already covers both Chart.js and the SDK bundle.
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
                    "https://cdn.jsdelivr.net",
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


# ---------------------------------------------------------------------------
# 6. Tic-tac-toe — server-side minimax AI, widget calls make_move.
# ---------------------------------------------------------------------------

@mcp.resource(
    "ui://tictactoe",
    mime_type="text/html;profile=mcp-app",
    meta={"ui": {"prefersBorder": True, "csp": _SDK_CSP}},
)
def tictactoe_app() -> str:
    return _load_app("06-tictactoe.html")


@mcp.tool(meta={"ui": {"resourceUri": "ui://tictactoe"}})
async def show_tictactoe() -> str:
    """Render a tic-tac-toe board. The widget calls back via `make_move`."""
    return "Tic-tac-toe rendered. You're X, AI is O."


def _winner(board: list[str]) -> str | None:
    lines = [(0,1,2),(3,4,5),(6,7,8),(0,3,6),(1,4,7),(2,5,8),(0,4,8),(2,4,6)]
    for a, b, c in lines:
        if board[a] and board[a] == board[b] == board[c]:
            return board[a]
    if all(board):
        return "draw"
    return None


def _minimax(board: list[str], me: str, opp: str, depth: int = 0) -> tuple[int, int]:
    """Returns (score, best_move). Score: +10 if `me` wins, -10 if `opp` wins."""
    w = _winner(board)
    if w == me:
        return 10 - depth, -1
    if w == opp:
        return depth - 10, -1
    if w == "draw":
        return 0, -1

    best_score = -999 if depth % 2 == 0 else 999
    best_move = -1
    for i in range(9):
        if board[i]:
            continue
        board[i] = me if depth % 2 == 0 else opp
        score, _ = _minimax(board, me, opp, depth + 1)
        board[i] = ""
        if depth % 2 == 0:
            if score > best_score:
                best_score, best_move = score, i
        else:
            if score < best_score:
                best_score, best_move = score, i
    return best_score, best_move


@mcp.tool()
async def make_move(board: list[str], move: int) -> dict:
    """Apply the player's move and return the AI's response.

    Args:
        board: 9-cell board, each "X" / "O" / "" (row-major).
        move: 0-8 index where the human (X) plays.

    Returns:
        {"board": list[str], "winner": "X"|"O"|"draw"|null, "ai_move": int|null}
    """
    if not isinstance(board, list) or len(board) != 9:
        raise ValueError("board must be 9 cells")
    if move < 0 or move > 8 or board[move] != "":
        raise ValueError("invalid move")

    new_board = list(board)
    new_board[move] = "X"

    w = _winner(new_board)
    if w:
        return {"board": new_board, "winner": w, "ai_move": None}

    _, ai_move = _minimax(new_board, "O", "X")
    if ai_move >= 0:
        new_board[ai_move] = "O"

    return {"board": new_board, "winner": _winner(new_board), "ai_move": ai_move}


# ---------------------------------------------------------------------------
# 7. Drawing canvas — large payload via callServerTool.
# ---------------------------------------------------------------------------

@mcp.resource(
    "ui://drawing",
    mime_type="text/html;profile=mcp-app",
    meta={"ui": {"prefersBorder": True, "csp": _SDK_CSP}},
)
def drawing_app() -> str:
    return _load_app("07-drawing.html")


@mcp.tool(meta={"ui": {"resourceUri": "ui://drawing"}})
async def show_drawing() -> str:
    """Render a drawing canvas. Submissions invoke `save_drawing`."""
    return "Drawing canvas rendered."


@mcp.tool()
async def save_drawing(title: str, data_url: str) -> str:
    """Receive a drawing from the show_drawing widget."""
    size = len(data_url)
    return f'Saved drawing "{title}" ({size:,} byte data URL).'


# ---------------------------------------------------------------------------
# 8. Todo list — multiple callServerTool round-trips.
# ---------------------------------------------------------------------------

@mcp.resource(
    "ui://todos",
    mime_type="text/html;profile=mcp-app",
    meta={"ui": {"prefersBorder": True, "csp": _SDK_CSP}},
)
def todos_app() -> str:
    return _load_app("08-todos.html")


@mcp.tool(meta={"ui": {"resourceUri": "ui://todos"}})
async def show_todos(items: list[str] | None = None) -> dict:
    """Render a todo list with optional initial items."""
    return {"items": items or []}


@mcp.tool()
async def add_todo(text: str) -> str:
    return f'Added todo: "{text}"'


@mcp.tool()
async def toggle_todo(text: str, done: bool) -> str:
    return f'{"Completed" if done else "Reopened"}: "{text}"'


@mcp.tool()
async def delete_todo(text: str) -> str:
    return f'Deleted todo: "{text}"'


# ---------------------------------------------------------------------------
# 9. Weather — Open-Meteo API (no auth).
# ---------------------------------------------------------------------------

@mcp.resource(
    "ui://weather",
    mime_type="text/html;profile=mcp-app",
    meta={
        "ui": {
            "prefersBorder": True,
            "csp": {
                "resourceDomains": ["https://cdn.jsdelivr.net"],
                "connectDomains": [
                    "https://geocoding-api.open-meteo.com",
                    "https://api.open-meteo.com",
                ],
            },
        }
    },
)
def weather_app() -> str:
    return _load_app("09-weather.html")


@mcp.tool(meta={"ui": {"resourceUri": "ui://weather"}})
async def show_weather(city: str = "San Francisco") -> str:
    """Render a current-conditions weather card for the given city."""
    return f"Weather for {city} rendered."


# ---------------------------------------------------------------------------
# 10. 3D viewer — three.js via CDN.
# ---------------------------------------------------------------------------

@mcp.resource(
    "ui://three-d",
    mime_type="text/html;profile=mcp-app",
    meta={"ui": {"prefersBorder": True, "csp": _SDK_CSP}},
)
def three_d_app() -> str:
    return _load_app("10-three-d.html")


@mcp.tool(meta={"ui": {"resourceUri": "ui://three-d"}})
async def show_3d(shape: str = "torus") -> str:
    """Render a rotating 3D shape (torus / cube / sphere / knot)."""
    return f"3D viewer rendered (shape={shape})."


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
