# Compliance checklist

Each app exercises a slice of the MCP-UI spec. A "fully compliant" host
should make every checkbox below pass without modification.

## Spec surface tested

**Resource delivery paths**

- [ ] `EmbeddedResource` with `mimeType: text/html` (inline `srcdoc`) — apps #1-3
- [ ] `EmbeddedResource` with `mimeType: text/uri-list` (parse URL, set as `src`) — app #4
- [ ] `ResourceLink` with external URI (use as `src` directly) — app #5

**postMessage actions (widget → host)**

- [ ] `size` (`{ height }`) — apps #2, #3, #4, #5
- [ ] `tool` (`{ toolName, params }`) — apps #3, #5
- [ ] `prompt` (`{ prompt }`) — app #3
- [ ] `link` (`{ url }`) — apps #4, #5
- [ ] `notify` (`{ message }`) — app #5
- [ ] `ui/request-display-mode` — app #15
- [ ] `ui/download-file` (with embedded blob) — app #17
- [ ] `ui/notifications/request-teardown` — app #18

**Resource `_meta.ui.csp` (CSP propagation)**

- [ ] `csp.resourceDomains` (CSP `script-src` / `img-src`) — apps #4, #5
- [ ] `csp.connectDomains` (CSP `connect-src`) — app #4
- [ ] `csp.frameDomains` (CSP `frame-src`) — app #20

**postMessage actions (host → widget)**

- [ ] `ui/notifications/host-context-changed` — apps #15, #16
- [ ] `ui/resource-teardown` — app #18

**_meta surfaces on tools**

- [ ] `_meta.ui.resourceUri` on every widget-emitting tool — apps #1-20
- [ ] `_meta.ui.visibility: ["app"]` (tool hidden from model) — `bump_counter` for app #19

**App capabilities advertised by widgets**

- [ ] `availableDisplayModes: ["inline", "fullscreen"]` — app #15

**Sandbox / security**

- [ ] Iframe `sandbox` attribute includes `allow-scripts` — required by #2-5
- [ ] Iframe sandbox does **not** include `allow-same-origin` — widgets must
      not be able to read host cookies or storage
- [ ] External CDN scripts load (`unpkg.com`, `cdn.jsdelivr.net`) — #4, #5
- [ ] Cross-origin `fetch()` from inside the iframe works — #4 (CoinGecko API)

## Per-app checklist

### 1. `show_hello` — Static card

- [ ] Renders as a card with the supplied `name`
- [ ] No console errors
- [ ] Iframe height is reasonable (does not collapse to 0)
- [ ] Server-rendered timestamp appears

**What this tests:** the simplest possible code path — static HTML with no
scripts. If this fails, the host's basic resource pipeline is broken.

### 2. `show_counter` — Dynamic resize

- [ ] +1 / −1 / Reset buttons update the displayed value
- [ ] Clicking "Grow ↓" reveals an extra panel
- [ ] **The iframe grows when the panel appears** — i.e. the host honored
      the `size` postMessage
- [ ] Clicking Reset shrinks the iframe back

**What this tests:** the `size` postMessage handler. A host that ignores it
will leave the iframe at its initial height, clipping content.

### 3. `show_feedback` — `callTool` and `sendPrompt`

- [ ] Star rating selects 1-5
- [ ] Submit is disabled until a rating is chosen
- [ ] Clicking "Reply with template" causes the host to send the user
      message `"Can you summarize the key points so far?"` to the model
      (i.e. the `prompt` postMessage was honored)
- [ ] Submitting the form invokes the `submit_feedback` tool on the host
      with `{ rating, text }` — verify by checking that the model receives
      a tool result like `Received feedback: 4/5 stars — "..."`
- [ ] Form is replaced by "✓ Submitted" after submit

**What this tests:** the two most consequential postMessage actions.
`tool` is what makes ext-apps interactive; `prompt` is what makes them
agent-aware. A host failing either is non-functional for any non-trivial
widget.

### 4. `show_price_chart` — External hosting + cross-origin

- [ ] Chart loads with current price for the given `symbol`
      (defaults to BTC; supports `BTC|ETH|SOL|DOGE|ADA`)
- [ ] 1D / 1W / 1M toggle reloads the chart
- [ ] Price color is green for positive % change, red for negative
- [ ] Clicking "Open on CoinGecko →" opens an external link
      (the host honored `link` postMessage)
- [ ] Skeleton shimmer appears briefly during load
- [ ] No mixed-content / CSP errors in the console

**What this tests:** the `text/uri-list` delivery path, external
script CDNs, and cross-origin `fetch` from a sandboxed iframe. This is
where most "almost-compliant" hosts trip — typically because their
iframe `sandbox` is too tight, or they strip the URI scheme.

### 5. `show_map` — Multi-callback

- [ ] Map renders with OSM tiles centered at the supplied `lat`, `lng`
- [ ] Clicking the map drops a pin at the click location
- [ ] **Each pin drop invokes the `save_pin` tool** — verify by checking
      tool result like `Saved pin at (48.8602, 2.3376) as "..."`
- [ ] If a label was typed, it's used; otherwise the lat/lng is used
- [ ] Each pin drop also fires a `notify` postMessage (host may toast or
      ignore — it should not error)
- [ ] Clicking a pin shows a popup with "Open in OSM →"
- [ ] Clicking the popup link opens an external URL (`link` postMessage)
- [ ] "Clear pins" removes all markers

**What this tests:** complex multi-callback flows, OSM tile loading
inside the sandbox, popups + delegated link handling. Mirrors the
real-world AllTrails-style widget.

### 15. `show_kanban` — Display modes

- [ ] Board renders with three columns stacked vertically (inline mode)
- [ ] Clicking "Maximize ⤢" calls `ui/request-display-mode { mode: "fullscreen" }`
- [ ] Host honors the request: widget receives `displayMode: "fullscreen"`
      either as the request result or via `host-context-changed`
- [ ] On `fullscreen`, columns lay out side-by-side; the badge text updates
- [ ] Clicking "Restore ⤡" returns to `inline` mode
- [ ] If the host toggles display mode externally, the widget reacts
      via `onhostcontextchanged` — no manual reload needed

**What this tests:** the display-mode round-trip plus the host-context
notification channel. A host that ignores `availableDisplayModes` will
likely also drop `request-display-mode` calls.

### 16. `show_themed_swatches` — Host design tokens

- [ ] Swatch grid renders with chips painted from `--color-*` variables
- [ ] The `theme:` / `platform:` / `locale:` / `tz:` / `mode:` pills
      reflect the host context (not "?")
- [ ] Toggling the host's light/dark theme triggers a re-render
      (chips and meta pills update without reload)
- [ ] If the host sends no `styles.variables`, each section shows
      "(host did not send any matching variables)" instead of breaking

**What this tests:** the `host-context-changed` notification path and the
host's commitment to keep `styles.variables` in sync with its actual theme.
Many hosts send variables once on init then never again.

### 17. `show_signature` — Native file download

- [ ] Drawing on the canvas activates the "Download PNG" button
- [ ] Clicking it invokes `ui/download-file` with an embedded
      `image/png` blob — the host opens its native save dialog
      (or auto-downloads, depending on platform)
- [ ] The widget reports `Downloaded "..."` or surfaces a clear
      error / cancel message
- [ ] "Clear" wipes the canvas and disables the download button

**What this tests:** the `ui/download-file` request — distinct from the
common pattern of round-tripping a payload through a callback tool.
Hosts that only implement `tools/call` will fail here even if every
other widget works.

### 18. `show_one_shot` — Self-dismissing widget

- [ ] Picking 👍 or 👎 enables the "Submit & dismiss" button
- [ ] Submitting invokes `submit_survey` on the server (model sees the result)
- [ ] After submit, the widget shows "Thanks — dismissing in 1s"
- [ ] One second later, the widget calls `ui/notifications/request-teardown`
      and the host removes the iframe (or leaves it but stops interaction)
- [ ] If the host fires `ui/resource-teardown` first, the log line at
      bottom turns red and reads `cleaned up (onteardown reason=…)`

**What this tests:** both teardown directions. Most hosts implement
neither; some implement only one. Splitting the test surfaces which.

### 19. `show_internal_counter` — Visibility scoping

- [ ] Widget renders showing value `0`
- [ ] Clicking "+1" calls `bump_counter` and the value increments,
      driven by the tool's `structuredContent.value`
- [ ] The visibility self-check shows two `pass` pills:
      `show_internal_counter` is in the model-visible tool list,
      `bump_counter` is **not**
- [ ] Asking the model directly to call `bump_counter` should fail —
      it should not be in the tool catalogue the model sees

**What this tests:** `_meta.ui.visibility: ["app"]`. A host that ignores
the field will leak the tool to the model — confusing, since `bump_counter`
takes no model-meaningful arguments and only makes sense from inside the
widget. (The self-check tries `tools/list` over the iframe channel; some
hosts don't expose it, in which case the pills show `skip` and the user
must verify manually.)

### 20. `show_url` — Generic URL-as-MCP-app wrapper

- [ ] Widget renders with the supplied `url` in the address bar and an
      iframe attempting to load it
- [ ] Default URL (`https://example.com`) loads cleanly — badge turns
      green and reads `framed`
- [ ] Clicking a URL pill (e.g. "OSM embed", "YT embed") loads that URL
- [ ] Pasting a URL whose origin is **not** in the resource's
      `_meta.ui.csp.frameDomains` fails with a CSP block — badge turns
      red and reads `blocked`; overlay says "Origin not in frameDomains"
- [ ] Loading an in-allowlist URL whose target sets
      `X-Frame-Options: DENY` fails differently — badge reads
      `X-Frame-Options?` after a ~4.5s timeout; overlay says "The target
      site refused framing"
- [ ] Clicking "Open ↗" invokes `ui/open-link` for the current URL
- [ ] Reload re-attempts the load

**What this tests:** `_meta.ui.csp.frameDomains` propagation. The host
must include allowlisted origins in its iframe's `frame-src` directive,
otherwise CSP will block the nested iframe even before the target site's
own framing policy is checked. Hosts that ignore `frameDomains` will
make every framing attempt fail with the CSP block, even for example.com.

## Round-trip verification

The callback tools (`submit_feedback`, `save_pin`, `make_move`,
`save_drawing`, `add_todo`/`toggle_todo`/`delete_todo`,
`record_punch_score`, `advance_adventure`, `record_florida_score`,
`submit_survey`, `bump_counter`) close the loop: the host sees the widget
call them as side effects of user interaction.

A host where the *widget renders* but the *callback tools never run* has
broken its postMessage handler — the widget might *look* fine while
being functionally inert. Always verify the round-trip, not just the
render.

## Non-goals

This suite is not a full security audit. It does not exercise:

- CSP evasion attempts
- Fingerprinting via timing or storage probes
- Iframe escape attempts
- Behavior under hostile widget content

Those belong in a separate red-team test suite.
