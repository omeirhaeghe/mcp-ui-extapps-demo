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


# ---------------------------------------------------------------------------
# 11. Punch the Monkey — timed clicker game.
# ---------------------------------------------------------------------------

@mcp.resource(
    "ui://punch-monkey",
    mime_type="text/html;profile=mcp-app",
    meta={"ui": {"prefersBorder": True, "csp": _SDK_CSP}},
)
def punch_monkey_app() -> str:
    return _load_app("11-punch-monkey.html")


@mcp.tool(meta={"ui": {"resourceUri": "ui://punch-monkey"}})
async def show_punch_monkey() -> str:
    """Render a 15-second punch-the-monkey clicker game."""
    return "Punch the monkey rendered. You have 15 seconds."


@mcp.tool()
async def record_punch_score(score: int, seconds: int) -> str:
    """Receive the final score from the punch_monkey widget."""
    ppm = (score * 60.0 / seconds) if seconds else 0.0
    return f"Score recorded: {score} punches in {seconds}s ({ppm:.0f}/min)."


# ---------------------------------------------------------------------------
# 12. Masquerade — Apple-II-style branching adventure. The picture lives
# in the widget; the user types their answer in the chat, the model
# translates it to advance_adventure(scene, answer).
# ---------------------------------------------------------------------------

@mcp.resource(
    "ui://adventure",
    mime_type="text/html;profile=mcp-app",
    meta={"ui": {"prefersBorder": True, "csp": _SDK_CSP}},
)
def adventure_app() -> str:
    return _load_app("12-adventure.html")


_SCENES: dict[str, dict] = {
    "gates": {
        "id": "gates",
        "art": "🏰",
        "title": "The Castle Gates",
        "description": (
            "Wrought-iron gates loom before you in the moonlight. Faint waltz music "
            "drifts from the castle. A masked butler peers through the bars. To one "
            "side, a low hedge marks the garden wall."
        ),
        "hint": "Knock, or sneak around through the garden?",
        "tone": None,
    },
    "butler": {
        "id": "butler",
        "art": "🎩",
        "title": "The Masked Butler",
        "description": (
            "The butler bows. \"State your business, traveller. The masquerade is "
            "by invitation only.\" His gloved hand extends, expectant."
        ),
        "hint": "Show the invitation, or claim to be a guest?",
        "tone": None,
    },
    "garden": {
        "id": "garden",
        "art": "🌹",
        "title": "The Moonlit Garden",
        "description": (
            "Roses glow silver in the moonlight. On a marble pedestal sits an ornate "
            "key beside a half-empty wine glass. A side door to the ballroom stands "
            "ajar."
        ),
        "hint": "Take the key, or slip through the door empty-handed?",
        "tone": None,
    },
    "ballroom": {
        "id": "ballroom",
        "art": "💃",
        "title": "The Ballroom",
        "description": (
            "Masked dancers spin under crystal chandeliers. A figure in a raven mask "
            "watches you from a balcony. Nearby, a server offers champagne — and "
            "discreetly, a folded note."
        ),
        "hint": "Approach the raven, or take the note?",
        "tone": "gold",
    },
    "raven": {
        "id": "raven",
        "art": "🪶",
        "title": "The Raven Mask",
        "description": (
            "The raven leans close. \"You shouldn't be here. But since you are — "
            "the host is not who they claim. Look behind the mirror in the library.\""
        ),
        "hint": "Head to the library, or confront the host directly?",
        "tone": "gold",
    },
    "library": {
        "id": "library",
        "art": "📜",
        "title": "Behind the Mirror",
        "description": (
            "The mirror swings open to reveal a hidden alcove. Inside: the real "
            "host, bound and gagged. Tonight's gala has been a charade. You've "
            "uncovered the masquerade."
        ),
        "hint": "Mystery solved.",
        "tone": "win",
    },
    "caught": {
        "id": "caught",
        "art": "⚔️",
        "title": "Caught",
        "description": (
            "Guards in plumed helmets seize your arms. \"Insolence!\" The "
            "imposter-host smiles thinly as you're dragged from the hall. The "
            "mystery dies with you."
        ),
        "hint": "Game over.",
        "tone": "lose",
    },
    "lost": {
        "id": "lost",
        "art": "🌫️",
        "title": "Lost in the Mist",
        "description": (
            "You wander too far from the castle and lose your bearings in the "
            "fog. By the time you find your way back, dawn has broken and the "
            "guests are gone."
        ),
        "hint": "Game over.",
        "tone": "lose",
    },
}

# (current_scene, normalized_keyword) -> next_scene
_TRANSITIONS: dict[tuple[str, str], str] = {
    ("gates", "knock"):       "butler",
    ("gates", "sneak"):       "garden",
    ("gates", "leave"):       "lost",
    ("butler", "invitation"): "ballroom",
    ("butler", "guest"):      "caught",
    ("butler", "lie"):        "caught",
    ("butler", "leave"):      "lost",
    ("garden", "key"):        "ballroom",
    ("garden", "door"):       "caught",
    ("garden", "wine"):       "caught",
    ("ballroom", "raven"):    "raven",
    ("ballroom", "note"):     "library",
    ("ballroom", "host"):     "caught",
    ("raven", "library"):     "library",
    ("raven", "host"):        "caught",
}

# Map common synonyms onto the canonical keyword used by _TRANSITIONS.
_SYNONYMS: dict[str, str] = {
    "knock on the door": "knock", "knock door": "knock",
    "sneak around": "sneak", "garden": "sneak", "hedge": "sneak",
    "leave": "leave", "go away": "leave", "give up": "leave",
    "show invitation": "invitation", "show the invitation": "invitation",
    "i'm a guest": "guest", "im a guest": "guest", "claim guest": "guest",
    "lie": "lie",
    "take key": "key", "take the key": "key", "grab key": "key",
    "go through door": "door", "use door": "door", "enter door": "door",
    "drink wine": "wine", "take wine": "wine",
    "approach raven": "raven", "talk to raven": "raven", "raven mask": "raven",
    "take note": "note", "read note": "note",
    "confront host": "host", "approach host": "host",
    "library": "library", "mirror": "library", "behind mirror": "library",
}


def _normalize(answer: str) -> str:
    a = (answer or "").strip().lower()
    if a in _SYNONYMS:
        return _SYNONYMS[a]
    for phrase, canonical in _SYNONYMS.items():
        if phrase in a:
            return canonical
    return a


@mcp.tool(meta={"ui": {"resourceUri": "ui://adventure"}})
async def show_adventure() -> dict:
    """Start the Masquerade adventure. The user reads the scene, then types
    their answer in chat — call advance_adventure to progress."""
    return {"scene": _SCENES["gates"]}


@mcp.tool(meta={"ui": {"resourceUri": "ui://adventure"}})
async def advance_adventure(scene: str, answer: str) -> dict:
    """Advance the Masquerade adventure.

    Args:
        scene: The current scene id (returned by the previous call).
        answer: The user's chat response. The server normalizes it and
                looks up the next scene. Unknown answers loop in place
                with an updated hint.
    """
    current = _SCENES.get(scene)
    if not current:
        return {"scene": _SCENES["gates"]}
    if current.get("tone") in ("win", "lose"):
        return {"scene": current}

    key = _normalize(answer)
    next_id = _TRANSITIONS.get((scene, key))
    if not next_id:
        retry = dict(current)
        retry["hint"] = f'Hmm — "{answer}" doesn\'t fit. {current.get("hint", "")}'
        return {"scene": retry}
    return {"scene": _SCENES[next_id]}


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
