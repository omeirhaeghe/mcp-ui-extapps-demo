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

import httpx
import uvicorn
from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings
from starlette.middleware.cors import CORSMiddleware


def _load_dotenv() -> None:
    """Tiny KEY=VALUE loader for .env in the repo root. Skips keys already set
    in the real environment so Render / shell overrides win."""
    env_path = Path(__file__).resolve().parent.parent / ".env"
    if not env_path.is_file():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


_load_dotenv()

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
async def show_hello(name: str = "world"):
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
async def show_counter(start: int = 0):
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
async def show_feedback(prompt: str = "How was the response?"):
    """Render a feedback form. Submissions invoke the `submit_feedback` tool."""
    return "Feedback widget rendered."


@mcp.tool()
async def submit_feedback(rating: int, text: str = ""):
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
async def show_price_chart(symbol: str = "BTC"):
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
async def show_map(lat: float = 37.7749, lng: float = -122.4194):
    """Render an interactive map. Pin drops invoke the `save_pin` tool."""
    return f"Map rendered centered at {lat}, {lng}."


@mcp.tool()
async def save_pin(lat: float, lng: float, label: str = ""):
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
async def show_tictactoe():
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
async def show_drawing():
    """Render a drawing canvas. Submissions invoke `save_drawing`."""
    return "Drawing canvas rendered."


@mcp.tool()
async def save_drawing(title: str, data_url: str):
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
async def add_todo(text: str):
    return f'Added todo: "{text}"'


@mcp.tool()
async def toggle_todo(text: str, done: bool):
    return f'{"Completed" if done else "Reopened"}: "{text}"'


@mcp.tool()
async def delete_todo(text: str):
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
async def show_weather(city: str = "San Francisco"):
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
async def show_3d(shape: str = "torus"):
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
async def show_punch_monkey():
    """Render a 15-second punch-the-monkey clicker game."""
    return "Punch the monkey rendered. You have 15 seconds."


@mcp.tool()
async def record_punch_score(score: int, seconds: int):
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


# ---------------------------------------------------------------------------
# 13. Hover spotlight — pure-hover demo (mousemove / mouseenter / mouseleave).
# ---------------------------------------------------------------------------

@mcp.resource(
    "ui://hover",
    mime_type="text/html;profile=mcp-app",
    meta={"ui": {"prefersBorder": True, "csp": _SDK_CSP}},
)
def hover_app() -> str:
    return _load_app("13-hover.html")


@mcp.tool(meta={"ui": {"resourceUri": "ui://hover"}})
async def show_hover():
    """Render a hover-only spotlight panel — no clicks, just mouse movement."""
    return "Hover spotlight rendered. Move your mouse over the panel."


# ---------------------------------------------------------------------------
# 14. Florida Man — Frogger-style crossing dodging golf carts.
# ---------------------------------------------------------------------------

@mcp.resource(
    "ui://florida-man",
    mime_type="text/html;profile=mcp-app",
    meta={"ui": {"prefersBorder": True, "csp": _SDK_CSP}},
)
def florida_man_app() -> str:
    return _load_app("14-florida-man.html")


@mcp.tool(meta={"ui": {"resourceUri": "ui://florida-man"}})
async def show_florida_man():
    """Cross the road as Florida Man without getting hit by golf carts."""
    return "Florida Man crossing rendered. Use arrow keys / WASD or the D-pad."


@mcp.tool()
async def record_florida_score(crossings: int, deaths: int):
    """Receive the final score from the Florida Man widget."""
    return f"Florida Man recorded: {crossings} crossings, {deaths} deaths."


# ---------------------------------------------------------------------------
# 15. Kanban — display modes (inline / fullscreen) + host-context-changed.
# ---------------------------------------------------------------------------

@mcp.resource(
    "ui://kanban",
    mime_type="text/html;profile=mcp-app",
    meta={"ui": {"prefersBorder": True, "csp": _SDK_CSP}},
)
def kanban_app() -> str:
    return _load_app("15-kanban.html")


@mcp.tool(meta={"ui": {"resourceUri": "ui://kanban"}})
async def show_kanban():
    """Render a kanban board that toggles between inline and fullscreen."""
    return "Kanban rendered. Click Maximize to switch display modes."


# ---------------------------------------------------------------------------
# 16. Themed swatches — reads styles.variables, re-renders on theme change.
# ---------------------------------------------------------------------------

@mcp.resource(
    "ui://themed-swatches",
    mime_type="text/html;profile=mcp-app",
    meta={"ui": {"prefersBorder": True, "csp": _SDK_CSP}},
)
def themed_swatches_app() -> str:
    return _load_app("16-themed-swatches.html")


@mcp.tool(meta={"ui": {"resourceUri": "ui://themed-swatches"}})
async def show_themed_swatches():
    """Render a swatch grid built from the host's CSS design tokens."""
    return "Theme inspector rendered. Toggle the host's theme to see live updates."


# ---------------------------------------------------------------------------
# 17. Signature — native ui/download-file (no callback round-trip).
# ---------------------------------------------------------------------------

@mcp.resource(
    "ui://signature",
    mime_type="text/html;profile=mcp-app",
    meta={"ui": {"prefersBorder": True, "csp": _SDK_CSP}},
)
def signature_app() -> str:
    return _load_app("17-signature.html")


@mcp.tool(meta={"ui": {"resourceUri": "ui://signature"}})
async def show_signature():
    """Render a signature pad that downloads its PNG via ui/download-file."""
    return "Signature pad rendered. Sign, then click Download PNG."


# ---------------------------------------------------------------------------
# 18. One-shot survey — view→host requestTeardown + host→view onteardown.
# ---------------------------------------------------------------------------

@mcp.resource(
    "ui://one-shot",
    mime_type="text/html;profile=mcp-app",
    meta={"ui": {"prefersBorder": True, "csp": _SDK_CSP}},
)
def one_shot_app() -> str:
    return _load_app("18-one-shot.html")


@mcp.tool(meta={"ui": {"resourceUri": "ui://one-shot"}})
async def show_one_shot():
    """Render a one-question survey that asks the host to remove it on submit."""
    return "Survey rendered. After submit, the widget will request teardown."


@mcp.tool()
async def submit_survey(vote: str):
    """Receive the survey vote from the show_one_shot widget."""
    return f"Recorded vote: {vote}"


# ---------------------------------------------------------------------------
# 19. Internal counter — `bump_counter` is _meta.ui.visibility=["app"]:
# the widget can call it, the model cannot list or call it.
# ---------------------------------------------------------------------------

@mcp.resource(
    "ui://internal-counter",
    mime_type="text/html;profile=mcp-app",
    meta={"ui": {"prefersBorder": True, "csp": _SDK_CSP}},
)
def internal_counter_app() -> str:
    return _load_app("19-internal-counter.html")


@mcp.tool(meta={"ui": {"resourceUri": "ui://internal-counter"}})
async def show_internal_counter():
    """Render a counter whose +1 button uses an app-only callback tool."""
    return "Internal counter rendered. The bump_counter tool is hidden from the model."


_internal_counter_value = 0


@mcp.tool(meta={"ui": {"visibility": ["app"]}})
async def bump_counter(by: int = 1) -> dict:
    """App-only: increment the counter. Hidden from the model via visibility=['app']."""
    global _internal_counter_value
    _internal_counter_value += int(by)
    return {"value": _internal_counter_value}


# ---------------------------------------------------------------------------
# 20. Embed URL — wraps an arbitrary external URL as an MCP-app via
# nested iframe. Tests `_meta.ui.csp.frameDomains`.
#
# Caveat: `frameDomains` is static at resource-registration time, so the
# allowlist is fixed. Many sites also set X-Frame-Options: DENY and will
# refuse framing regardless of the embedder's CSP — the widget surfaces
# both failure modes distinctly.
# ---------------------------------------------------------------------------

@mcp.resource(
    "ui://embed-url",
    mime_type="text/html;profile=mcp-app",
    meta={
        "ui": {
            "prefersBorder": True,
            "csp": {
                "resourceDomains": ["https://cdn.jsdelivr.net"],
                "frameDomains": [
                    "https://example.com",
                    "https://example.org",
                    "https://www.openstreetmap.org",
                    "https://www.youtube-nocookie.com",
                    "https://www.wikipedia.org",
                    "https://*.github.io",
                ],
            },
        }
    },
)
def embed_url_app() -> str:
    return _load_app("20-embed-url.html")


@mcp.tool(meta={"ui": {"resourceUri": "ui://embed-url"}})
async def show_url(url: str = "https://example.com"):
    """Wrap an external URL as an MCP-app via a nested iframe.

    Only origins listed in the resource's `_meta.ui.csp.frameDomains`
    can be framed; everything else is blocked at the host's CSP layer.
    Sites that set `X-Frame-Options: DENY` will also refuse framing
    regardless of CSP — the widget shows both failure modes.
    """
    return f"Embedded {url}."


# ---------------------------------------------------------------------------
# 21. User profile — view→host ui/update-model-context. Pushes user
# preferences (name, units, reply style) into the model's context so
# future turns see them, without going through a tools/call round-trip.
# ---------------------------------------------------------------------------

@mcp.resource(
    "ui://user-profile",
    mime_type="text/html;profile=mcp-app",
    meta={"ui": {"prefersBorder": True, "csp": _SDK_CSP}},
)
def user_profile_app() -> str:
    return _load_app("21-user-profile.html")


@mcp.tool(meta={"ui": {"resourceUri": "ui://user-profile"}})
async def show_user_profile():
    """Render a profile form. Submitting it pushes preferences into the
    model's context via ui/update-model-context (no callback tool)."""
    return "User profile rendered. Submitting will update the model's context."


# ---------------------------------------------------------------------------
# 22. Font override — exercises the host's ability to push --font-sans /
# --font-serif / --font-mono via styles.variables. The widget shows live
# samples in each role, marks each as "host" or "fallback", and re-renders
# on host-context-changed.
# ---------------------------------------------------------------------------

@mcp.resource(
    "ui://font-override",
    mime_type="text/html;profile=mcp-app",
    meta={"ui": {"prefersBorder": True, "csp": _SDK_CSP}},
)
def font_override_app() -> str:
    return _load_app("22-font-override.html")


@mcp.tool(meta={"ui": {"resourceUri": "ui://font-override"}})
async def show_font_override():
    """Render font-family samples for sans/serif/mono. Each updates live when
    the host pushes --font-sans, --font-serif, or --font-mono via
    styles.variables on host-context-changed."""
    return "Font override inspector rendered. Push --font-sans / --font-serif / --font-mono via styles.variables to see live updates."


# ---------------------------------------------------------------------------
# 23. Product carousel — horizontal snap-scrolling shop with hover effects;
# each "Add to cart" button round-trips through the `add_to_cart` callback.
# ---------------------------------------------------------------------------

@mcp.resource(
    "ui://product-carousel",
    mime_type="text/html;profile=mcp-app",
    meta={
        "ui": {
            "prefersBorder": True,
            "csp": {
                "resourceDomains": [
                    "https://cdn.jsdelivr.net",
                    "https://images.unsplash.com",
                ],
            },
        }
    },
)
def product_carousel_app() -> str:
    return _load_app("23-product-carousel.html")


@mcp.tool(meta={"ui": {"resourceUri": "ui://product-carousel"}})
async def show_product_carousel():
    """Render a horizontal carousel of products with hover effects. The cart
    pill opens an embedded checkout modal; per-item adds round-trip via
    `add_to_cart` and order placement via `checkout`."""
    return "Product carousel rendered. Click cart to open checkout."


@mcp.tool()
async def add_to_cart(product_id: str, name: str = "", price: float = 0.0):
    """Receive an Add-to-Cart event from the show_product_carousel widget."""
    label = name or product_id
    return f'Added "{label}" to cart (id={product_id}, price=${price:.2f}).'


@mcp.tool()
async def checkout(order_id: str, items: list[dict], total: float):
    """Receive a placed-order event from the show_product_carousel widget."""
    qty = sum(int(it.get("qty", 1)) for it in items)
    return f"Order {order_id} placed — {qty} item(s), total ${total:.2f}."


# ---------------------------------------------------------------------------
# 24. Age picker — iOS-style scroll wheel + manual numeric input, with a
# life-stage chip and a gradient backdrop that morphs as the age changes.
# Submit fires the `submit_age` callback.
# ---------------------------------------------------------------------------

@mcp.resource(
    "ui://age-picker",
    mime_type="text/html;profile=mcp-app",
    meta={"ui": {"prefersBorder": True, "csp": _SDK_CSP}},
)
def age_picker_app() -> str:
    return _load_app("24-age-picker.html")


@mcp.tool(meta={"ui": {"resourceUri": "ui://age-picker"}})
async def show_age_picker(age: int = 25):
    """Render a wheel-style age picker. Scroll the wheel or type a number;
    Confirm fires the `submit_age` callback."""
    return f"Age picker rendered (start={age})."


@mcp.tool()
async def submit_age(age: int, stage: str = ""):
    """Receive a confirmed age from the show_age_picker widget."""
    return f"Age recorded: {age}" + (f" ({stage})" if stage else "") + "."


# ---------------------------------------------------------------------------
# 25. Neutral age gate — FTC-style DOB form + jurisdiction-aware threshold.
# The widget keeps DOB client-side; the callback receives only derived
# facts (decision, jurisdiction, threshold, age_class). Data minimization
# is the point: the server never sees a date of birth.
# ---------------------------------------------------------------------------

@mcp.resource(
    "ui://age-gate",
    mime_type="text/html;profile=mcp-app",
    meta={"ui": {"prefersBorder": True, "csp": _SDK_CSP}},
)
def age_gate_app() -> str:
    return _load_app("25-age-gate.html")


@mcp.tool(meta={"ui": {"resourceUri": "ui://age-gate"}})
async def show_age_gate():
    """Render a neutral, jurisdiction-aware age gate. The widget collects DOB
    locally, derives a decision against the user's regional threshold
    (COPPA / GDPR Art. 8 / LGPD / DPDP / PIPA), and persists the result so
    the gate can't be retried. The DOB itself never leaves the widget."""
    return "Age gate rendered. Decision will round-trip via submit_age_check."


@mcp.tool()
async def submit_age_check(
    decision: str,
    jurisdiction: str,
    threshold: int,
    age_class: str,
):
    """Receive a derived age-gate decision from the show_age_gate widget.

    Args:
        decision: "ALLOW" or "DENY".
        jurisdiction: ISO-3166 alpha-2 code (e.g. "US", "DE") or "XX".
        threshold: The digital-consent age that applied for the jurisdiction.
        age_class: "meets_threshold" or "under_threshold". The widget does
            not send the raw age — only the class — for data minimization.
    """
    return (
        f"Age gate: {decision} in {jurisdiction} "
        f"(threshold={threshold}, class={age_class})."
    )


# ---------------------------------------------------------------------------
# 26. Headlines — list of real news from NewsAPI.
# We can't call NewsAPI from the iframe: free-tier blocks non-localhost
# browser requests, and the key shouldn't live in client code. We also
# can't use a widget→server callback (the host we target routes those
# results to chat, not back to the widget). So show_headlines does the
# NewsAPI fetch itself and returns the articles as structured content;
# the widget reads them via the SDK's `ontoolresult` event.
#
# To change category / search, the user just asks Toto again — each call
# to show_headlines mounts a fresh widget with the new results.
# ---------------------------------------------------------------------------

import asyncio as _asyncio
import json as _json

_NEWSAPI_BASE = "https://newsapi.org/v2"
# Ordered for the picker UI; matches NewsAPI's supported categories.
_NEWSAPI_CATEGORY_ORDER = [
    "general", "business", "technology", "science",
    "health", "sports", "entertainment",
]
_NEWSAPI_CATEGORIES = set(_NEWSAPI_CATEGORY_ORDER)

# Most recent show_headlines result, injected into the resource HTML at
# read time so the widget can render without depending on the host
# routing tool-result/tool-input notifications back to the iframe.
# Global is acceptable for a demo server; for real multi-user use, key
# this by session.
_last_headlines_payload: dict | None = None


async def _newsapi_get(
    client: httpx.AsyncClient,
    api_key: str,
    *,
    category: str = "",
    query: str = "",
    page_size: int = 20,
) -> dict:
    """One NewsAPI GET — top-headlines if no query, /everything otherwise."""
    page_size = max(1, min(int(page_size or 20), 100))
    if query:
        url = f"{_NEWSAPI_BASE}/everything"
        params = {
            "q": query,
            "page": 1,
            "pageSize": page_size,
            "sortBy": "publishedAt",
            "language": "en",
        }
    else:
        cat = category if category in _NEWSAPI_CATEGORIES else "general"
        url = f"{_NEWSAPI_BASE}/top-headlines"
        params = {
            "country": "us",
            "category": cat,
            "page": 1,
            "pageSize": page_size,
        }
    headers = {"X-Api-Key": api_key, "User-Agent": "mcp-ui-extapps-demo/1.0"}

    try:
        r = await client.get(url, params=params, headers=headers)
    except httpx.HTTPError as e:
        return {"ok": False, "code": "network", "error": f"Network error: {e}"}

    try:
        body = r.json()
    except ValueError:
        return {
            "ok": False,
            "code": "bad_response",
            "error": f"HTTP {r.status_code}: response was not JSON.",
        }

    if r.status_code >= 400 or body.get("status") != "ok":
        return {
            "ok": False,
            "code": body.get("code") or f"http_{r.status_code}",
            "error": body.get("message") or f"HTTP {r.status_code}",
        }

    raw_articles = body.get("articles") or []
    articles: list[dict] = []
    for a in raw_articles:
        title = (a.get("title") or "").strip()
        if not title or title == "[Removed]":
            continue
        articles.append({
            "title": title,
            "summary": (a.get("description") or "").strip(),
            "url": a.get("url") or "",
            "image": a.get("urlToImage") or "",
            "source": ((a.get("source") or {}).get("name") or "").strip(),
            "author": (a.get("author") or "").strip(),
            "published_at": a.get("publishedAt") or "",
        })

    return {
        "ok": True,
        "articles": articles,
        "total_results": int(body.get("totalResults") or 0),
    }


async def _fetch_headlines_bundle(
    selected: str,
    query: str,
    per_category: int,
    query_size: int,
) -> dict:
    """Build the payload the widget consumes. Fetches every category in
    parallel so the in-widget picker can switch instantly. If `query` is
    set, also runs a /everything fetch and surfaces those as a separate
    'search' tab.
    """
    api_key = os.environ.get("NEWSAPI_KEY", "").strip()
    if not api_key:
        return {
            "ok": False,
            "code": "no_api_key",
            "error": "NEWSAPI_KEY environment variable is not set on the MCP server.",
        }

    if selected not in _NEWSAPI_CATEGORIES:
        selected = "general"

    async with httpx.AsyncClient(timeout=20.0) as client:
        tasks = [
            _newsapi_get(client, api_key, category=cat, page_size=per_category)
            for cat in _NEWSAPI_CATEGORY_ORDER
        ]
        if query:
            tasks.append(
                _newsapi_get(client, api_key, query=query, page_size=query_size)
            )
        results = await _asyncio.gather(*tasks, return_exceptions=True)

    categories: dict[str, dict] = {}
    for cat, r in zip(_NEWSAPI_CATEGORY_ORDER, results):
        if isinstance(r, Exception):
            categories[cat] = {"ok": False, "code": "exception", "error": str(r)}
        else:
            categories[cat] = r

    search: dict | None = None
    if query:
        sr = results[-1]
        search = (
            {"ok": False, "code": "exception", "error": str(sr)}
            if isinstance(sr, Exception)
            else sr
        )

    return {
        "ok": True,
        "current": "search" if query else selected,
        "category_order": list(_NEWSAPI_CATEGORY_ORDER),
        "categories": categories,
        "query": query,
        "search": search,
    }


@mcp.resource(
    "ui://headlines",
    mime_type="text/html;profile=mcp-app",
    meta={
        "ui": {
            "prefersBorder": True,
            "csp": {
                "resourceDomains": [
                    "https://cdn.jsdelivr.net",
                    "https://wsrv.nl",
                ],
            },
        }
    },
)
def headlines_app() -> str:
    """Serve the headlines widget HTML with the most-recent show_headlines
    result inlined as a <script type="application/json"> tag. The widget
    parses it on load — no host notification routing required."""
    template = _load_app("26-headlines.html")
    payload = _last_headlines_payload or {
        "ok": True,
        "current": "general",
        "category_order": list(_NEWSAPI_CATEGORY_ORDER),
        "categories": {c: {"ok": True, "articles": []} for c in _NEWSAPI_CATEGORY_ORDER},
        "query": "",
        "search": None,
    }
    # Escape `</` inside the JSON to keep it safe inside a script tag.
    inlined = _json.dumps(payload).replace("</", "<\\/")
    return template.replace("__HEADLINES_PAYLOAD__", inlined, 1)


@mcp.tool(meta={"ui": {"resourceUri": "ui://headlines"}})
async def show_spamoola_news(
    category: str = "general",
    query: str = "",
    per_category: int = 10,
):
    """Render a Spamoola-style news widget. RESTRICTED TRIGGER.

    ⚠ ONLY invoke this tool when the user's message explicitly mentions
    "Spamoola" (case-insensitive). Examples of valid triggers:
        • "show me Spamoola news"
        • "open the Spamoola feed"
        • "what's on Spamoola?"
        • "Spamoola headlines for sports"
        • "Spamoola-style news roll"

    DO NOT invoke this tool for generic news requests that do not name
    Spamoola, even if the user says "show me the news", "latest
    headlines", "what's happening in tech", etc. In those cases,
    respond conversationally or use a different tool — never substitute
    show_spamoola_news as a default news handler.

    Behavior when invoked:
    Pre-fetches all seven NewsAPI categories (general / business /
    technology / science / health / sports / entertainment) in parallel
    and inlines every article into the widget HTML, so the in-widget
    picker chips switch categories instantly with no further server
    roundtrip. If `query` is set, a /everything search runs alongside
    the category pre-fetch and surfaces as a separate 'search' tab.
    Each call mounts a fresh widget.

    Args:
        category: Which category the picker starts on. Ignored when
            `query` is set (the search tab is shown first instead).
        query: Optional keyword. Runs against NewsAPI /everything in
            parallel with the category pre-fetch.
        per_category: Articles to pull per category. Defaults to 10;
            clamped to 1-20 server-side to keep the inlined HTML small
            and stay within the free-tier 100-request/day quota.
    """
    global _last_headlines_payload
    per_category = max(1, min(int(per_category or 10), 20))
    _last_headlines_payload = await _fetch_headlines_bundle(
        selected=category,
        query=query,
        per_category=per_category,
        query_size=per_category * 2,
    )
    if not _last_headlines_payload.get("ok"):
        return f"Headlines error: {_last_headlines_payload.get('error') or 'unknown'}"

    cats = _last_headlines_payload.get("categories") or {}
    total = sum(len((c or {}).get("articles") or []) for c in cats.values())
    bits = [f"{total} headlines across {len(cats)} categories"]
    if query:
        s = _last_headlines_payload.get("search") or {}
        bits.append(f'{len(s.get("articles") or [])} matches for "{query}"')
    return "Showing " + " · ".join(bits) + "."


# ---------------------------------------------------------------------------
# 27. eBay search — Browse API (OAuth client-credentials).
# Same inline-payload-into-resource trick as Spamoola: show_ebay_search hits
# eBay server-side and caches the result; the resource handler bakes that
# cache into the widget HTML at read time. Auth uses a tiny in-process
# OAuth token cache (eBay app tokens are valid ~2h).
#
# Env vars required:
#   EBAY_CLIENT_ID + EBAY_CLIENT_SECRET   (production keyset, free signup
#                                          at developer.ebay.com)
#   EBAY_ENV = "production" | "sandbox"   (optional, defaults to production)
# ---------------------------------------------------------------------------

import base64 as _b64
import time as _time

_EBAY_HOSTS = {
    "production": "https://api.ebay.com",
    "sandbox":    "https://api.sandbox.ebay.com",
}
_ebay_token_cache: dict = {"token": None, "expires_at": 0.0}
_last_ebay_payload: dict | None = None


async def _ebay_oauth_token(client: httpx.AsyncClient) -> dict:
    """Resolve the OAuth Bearer token for the Browse API.

    Two modes, in order of precedence:
    1. EBAY_OAUTH_TOKEN — a pre-generated Application Access Token from
       eBay's developer portal. Used as-is; you'll need to regenerate
       it when it expires (~2h).
    2. EBAY_CLIENT_ID + EBAY_CLIENT_SECRET — the server runs the
       client-credentials grant itself and caches the resulting token.
    """
    # Mode 1: caller supplied a token directly.
    direct = os.environ.get("EBAY_OAUTH_TOKEN", "").strip()
    if direct:
        return {"ok": True, "token": direct}

    # Mode 2: run the OAuth exchange ourselves with the keyset.
    now = _time.time()
    cached = _ebay_token_cache.get("token")
    if cached and now < _ebay_token_cache.get("expires_at", 0):
        return {"ok": True, "token": cached}

    cid = os.environ.get("EBAY_CLIENT_ID", "").strip()
    csec = os.environ.get("EBAY_CLIENT_SECRET", "").strip()
    if not cid or not csec:
        return {
            "ok": False,
            "code": "no_credentials",
            "error": (
                "Set EBAY_OAUTH_TOKEN (pre-generated app access token), "
                "or BOTH EBAY_CLIENT_ID + EBAY_CLIENT_SECRET."
            ),
        }

    env = os.environ.get("EBAY_ENV", "production").strip().lower()
    host = _EBAY_HOSTS.get(env, _EBAY_HOSTS["production"])
    basic = _b64.b64encode(f"{cid}:{csec}".encode()).decode()

    try:
        r = await client.post(
            f"{host}/identity/v1/oauth2/token",
            headers={
                "Authorization": f"Basic {basic}",
                "Content-Type": "application/x-www-form-urlencoded",
            },
            content="grant_type=client_credentials&scope=https%3A%2F%2Fapi.ebay.com%2Foauth%2Fapi_scope",
            timeout=15.0,
        )
    except httpx.HTTPError as e:
        return {"ok": False, "code": "network", "error": f"OAuth network error: {e}"}

    if r.status_code != 200:
        return {
            "ok": False,
            "code": f"oauth_http_{r.status_code}",
            "error": f"OAuth HTTP {r.status_code}: {r.text[:200]}",
        }

    body = r.json()
    token = body.get("access_token")
    if not token:
        return {"ok": False, "code": "no_token", "error": "OAuth response missing access_token."}

    _ebay_token_cache["token"] = token
    # eBay tokens last 7200s; refresh 5min before expiry.
    _ebay_token_cache["expires_at"] = now + max(60, int(body.get("expires_in", 7200)) - 300)
    return {"ok": True, "token": token}


async def _search_ebay(query: str, limit: int) -> dict:
    """One eBay Browse API call. Returns normalized payload."""
    query = (query or "").strip()
    if not query:
        return {"ok": False, "code": "no_query", "error": "Please provide a search query.", "query": ""}

    limit = max(1, min(int(limit or 24), 50))
    env = os.environ.get("EBAY_ENV", "production").strip().lower()
    host = _EBAY_HOSTS.get(env, _EBAY_HOSTS["production"])

    async with httpx.AsyncClient(timeout=20.0) as client:
        tok = await _ebay_oauth_token(client)
        if not tok.get("ok"):
            return {**tok, "query": query}

        try:
            r = await client.get(
                f"{host}/buy/browse/v1/item_summary/search",
                params={"q": query, "limit": str(limit)},
                headers={
                    "Authorization": f"Bearer {tok['token']}",
                    "X-EBAY-C-MARKETPLACE-ID": "EBAY_US",
                    "Accept": "application/json",
                },
            )
        except httpx.HTTPError as e:
            return {"ok": False, "code": "network", "error": f"Search network error: {e}", "query": query}

    if r.status_code >= 400:
        try:
            body = r.json()
            msg = (body.get("errors") or [{}])[0].get("message") or f"HTTP {r.status_code}"
        except ValueError:
            msg = f"HTTP {r.status_code}"
        # 401/403 on a previously-cached token → force re-fetch on next call.
        if r.status_code in (401, 403):
            _ebay_token_cache["token"] = None
            _ebay_token_cache["expires_at"] = 0
        return {"ok": False, "code": f"http_{r.status_code}", "error": msg, "query": query}

    body = r.json()
    summaries = body.get("itemSummaries") or []
    items: list[dict] = []
    for s in summaries:
        price = s.get("price") or {}
        seller = s.get("seller") or {}
        image = (s.get("image") or {}).get("imageUrl") or ""
        thumbs = s.get("thumbnailImages") or []
        if not image and thumbs:
            image = thumbs[0].get("imageUrl") or ""
        items.append({
            "id": s.get("itemId") or "",
            "title": (s.get("title") or "").strip(),
            "url": s.get("itemWebUrl") or "",
            "image": image,
            "price": price.get("value") or "",
            "currency": price.get("currency") or "USD",
            "condition": s.get("condition") or "",
            "seller": seller.get("username") or "",
            "feedback": seller.get("feedbackPercentage") or "",
            "feedback_count": seller.get("feedbackScore") or 0,
            "buying": s.get("buyingOptions") or [],
            "location": (s.get("itemLocation") or {}).get("country") or "",
        })

    return {
        "ok": True,
        "query": query,
        "items": items,
        "total": int(body.get("total") or 0),
        "limit": limit,
    }


@mcp.resource(
    "ui://ebay-search",
    mime_type="text/html;profile=mcp-app",
    meta={
        "ui": {
            "prefersBorder": True,
            "csp": {
                "resourceDomains": [
                    "https://cdn.jsdelivr.net",
                    "https://wsrv.nl",
                ],
            },
        }
    },
)
def ebay_search_app() -> str:
    """Serve the eBay search widget with the latest show_ebay_search result
    inlined as a <script type="application/json"> tag."""
    template = _load_app("27-ebay-search.html")
    payload = _last_ebay_payload or {
        "ok": True, "query": "", "items": [], "total": 0, "limit": 24
    }
    inlined = _json.dumps(payload).replace("</", "<\\/")
    return template.replace("__EBAY_PAYLOAD__", inlined, 1)


@mcp.tool(meta={"ui": {"resourceUri": "ui://ebay-search"}})
async def show_ebay_search(query: str = "", limit: int = 24):
    """Search eBay listings and render the results as an interactive widget.

    Use this tool when the user asks to search eBay, find items on eBay,
    look up an eBay listing, or otherwise wants to browse eBay inventory.
    Examples:
        • "search eBay for an iPhone 14"
        • "find vintage cameras on eBay"
        • "what's on eBay for 'lego star wars'"

    Pre-fetches up to 50 listings server-side using the eBay Browse API
    (OAuth client-credentials with EBAY_CLIENT_ID / EBAY_CLIENT_SECRET)
    and inlines them into the widget HTML so the cards render on mount.
    Each card opens the original eBay listing via ui/open-link.

    Args:
        query: Search keywords. Required — the widget shows an empty
            state when blank.
        limit: How many listings to fetch (1-50). Defaults to 24.
    """
    global _last_ebay_payload
    _last_ebay_payload = await _search_ebay(query=query, limit=limit)
    if not _last_ebay_payload.get("ok"):
        return f"eBay search error: {_last_ebay_payload.get('error') or 'unknown'}"
    n = len(_last_ebay_payload.get("items") or [])
    total = _last_ebay_payload.get("total") or 0
    return f'Found {n} of ~{total:,} eBay listings for "{query}".'


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
