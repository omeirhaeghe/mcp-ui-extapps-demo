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

## Round-trip verification

The two callback tools (`submit_feedback`, `save_pin`) close the loop:
the host sees the widget call them as side effects of user interaction.

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
