# DESIGN — PIKSTOCK Keyword Generator

Locked design system for the local web UI, derived from the code that exists today
(`web/index.html`, `web/components.css`, `web/js/`). Every value below was read from
those files; each row carries its source line. Where the code cannot answer, the
text says `UNVERIFIED — <reason>`. Status: **descriptive of current state, with a drift register**. It records what is,
which anti-slop floor items pass, and which fail. Changing the UI without updating
this file breaks the lock.

---

## 1. Context

| Field | Value | Source |
|---|---|---|
| Product name | PIKSTOCK | `index.html:7` (`<title>PIKSTOCK — Keyword Generator</title>`) |
| What it is | Local tool: upload image(s), an LLM writes marketplace keyword sets | `index.html:64-70`; `web/js/markets.js` `MARKETS` |
| Markets covered | Etsy, Canva, Creative Market, Universal stock, Adobe Stock | `web/js/markets.js`, `index.html:291-299` |
| Users | One person on their own machine, bound to `127.0.0.1` | `server.py` docstring, `app.py` docstring |
| Shell | One SPA document, five `<section>` views toggled by `hidden` | `index.html`: `view-single`, `view-batch`, `view-extract`, `view-history`, `view-settings` |
| Overlays | Result drawer, toast, two sticky bars | `web/components.css .drawer`.toast`.staged-bar`.batch-bar` |
| Language | Indonesian copy, `lang="id"` | `index.html:2` |
| Theme | Dark only. `color-scheme: dark`, `theme-color #14110d` | `index.html:5-6` |
| Direction | "studio kraft" — warm dark paper, amber stamp accent, serif display | `web/components.css` header comment |
| Icons | Inline SVG only, no icon font, no icon library | `index.html` nav items; `web/js/ui.js emptyHTML` |
| Runtime | FastAPI mounts `web/` at `/static`, serves `index.html` at `/` | `server.py:504`, `server.py:507-509` |
| Cache policy | `/static/*` forced `Cache-Control: no-cache` so CSS/JS edits apply on refresh | `server.py:38-48` |
| File size | `index.html` 410 lines, `web/components.css` 741 lines, `web/js/` 2239 lines | measured 2026-11-10 | This is **an existing system**. The job is match-and-extend, not redesign.

---

## 2. Principles

Each is a rule the code already follows, not a brief.

1. **Result first, chrome quiet.** A 248px sidebar plus a centred 1100px column (`web/layout.css .app`). Nav ink is `--txt-dim`; only the active item gets accent (`web/layout.css .nav-item`). Display serif is reserved for names and headings.
2. **State is colour *and* shape.** Signal strength is a border tint plus a leading dot (`web/components.css .chip.sig-*`); the legend repeats the dot alone (`web/components.css .sig-legend`), so it survives greyscale.
3. **Every async action shows local progress.** Skeleton before results (`web/components.css .skel-*`), per-image spinner (`web/components.css .spinner`), batch progress bar (`web/components.css .progress`), busy-state staged cards (`web/components.css .tc-state`).
4. **Destructive actions are reversible or confirmed.** 5.2 s undo toast (`web/js/history.js`), `confirm()` before clear-all (`web/js/history.js`).
5. **Keyboard is a real path.** Chips are `<button>` (`web/js/render.js`), history rows are `role="button" tabindex="0"` (`web/js/history.js`), dropzone answers Enter/Space (`web/js/upload.js`), drawer answers ←/→/Escape (`web/js/history.js drawer`).
6. **Motion is optional and respectful.** Motion One is loaded, but every animation is gated on `!reduced` (`web/js/ui.js`) and CSS kills transitions under `prefers-reduced-motion` (`web/responsive.css`).
7. **No dependency for a small thing.** No framework, no bundler, no CSS preprocessor, no icon package. Plain script, hand-written CSS.

---

## 3. Tokens

Declared in `:root` at `web/tokens.css` — **129 custom properties** (surfaces, ink,
accent fills/lines, semantic ink/fill/line families, neutral layers, shape, spacing).
Reference counts measured across `web/tokens.css`, `web/layout.css`,
`web/components.css`, `web/responsive.css`, excluding declarations. **Token expansion closed the literal debt.** Target reached: 0 colour literals outside
`:root` in every stylesheet; every `var()` in the CSS resolves to a declared token
(verified by script).
### Surfaces

| Token | Value | Role | Refs |
|---|---|---|---|
| `--bg` | `#14110d` | page base, warm near-black | 3 |
| `--bg-soft` | `#191510` | drawer surface | 1 (`web/components.css .drawer`) |
| `--panel` | `#1e1913` | card, skeleton, log row, history row | 7 |
| `--panel-2` | `#262019` | raised surface, row hover | 2 |
| `--line` | `#332b21` | border of interactive surfaces | 13 |
| `--line-soft` | `#29221a` | border of passive surfaces | 18 |
### Ink

| Token | Value | Role | Refs | Contrast on `--bg` |
|---|---|---|---|---|
| `--txt` | `#f3ede2` | body ink | 8 | 15.6:1 |
| `--txt-dim` | `#c2b6a4` | secondary ink, nav | 12 | 9.2:1 |
| `--txt-faint` | `#928776` | labels, counts, hints | 28 | 4.9:1 |
### Accent and semantic

| Token | Value | Role | Refs |
|---|---|---|---|
| `--accent` | `#e8a33d` | primary action, active nav, signal "sedang" | 17 |
| `--accent-soft` | `#f4c579` | gradient top stop, hover ink on accent surfaces | 9 |
| `--accent-ink` | `#201709` | ink **on** amber fills (4.9:1 on `#e8a33d`) | 3 |
| `--ok` | `#56c08b` | success, signal "kuat" | 5 |
| `--warn` | `#e8a33d` | **never referenced** — identical to `--accent` | **0** |
| `--bad` | `#e2685f` | failure, over-limit chip | 4 |
### Shape, depth, type

| Token | Value | Role | Refs |
|---|---|---|---|
| `--radius` | `14px` | cards, panels, skeleton, settings cards | 5 |
| `--radius-sm` | `9px` | **never referenced** | **0** |
| `--shadow` | `0 24px 60px -28px rgba(0,0,0,.9)` | floating bars, drawer, toast | 3 |
| `--ring` | `0 0 0 2px var(--bg), 0 0 0 4px rgba(232,163,61,.75)` | `:focus-visible` | in token only |
| `--font-display` | `"Fraunces","Iowan Old Style",Georgia,serif` | headings, card titles, names | 9 |
| `--font-body` | `"Plex Sans","Segoe UI",system-ui,-apple-system,sans-serif` | everything else | via `body` |
| `--font-mono` | `ui-monospace,"Cascadia Code",Consolas,monospace` | inline `<code>`, textarea | 1 |
| `--s1..--s7` | `4,8,12,16,22,32,48px` | spacing scale | see §6 |
### Token drift (resolved 2026-11-10)

| Issue | Was | Now |
|---|---|---|
| `--warn` duplicated `--accent` | `#e8a33d`, 0 refs | removed; amber is `--accent`, caution is `--accent-hover` on `.rh-warn` |
| `--radius-sm` unused | `9px`, 0 refs | now used by `.btn`, `.input`, `.icon-btn`, `.seg`, `.log-row`, `.seg-btn` |
| `--s1..--s7` declared, not driving layout | 0 refs on four tokens | spacing scale extended (`--s1h --s1t --s1q --s2q --s3q --s3h --s3w`) and applied to every `gap` and most `padding` |
| `--s5: 22px` off the 4px step | 22px | **24px** (4px step restored) |
| `--ring` second stop was a literal | `rgba(232,163,61,.75)` | `var(--accent-line-75)` |
| 124 colour literals outside `:root` | measured | **0** — all migrated to token families |
| JS-injected `#f6c76a` | `render.js` inline style | `.rh-warn` class, `var(--accent-hover)` |
| Inline `style=` in skeleton markup | `ui.js` | `.skel-meta`, `.skel-w-42`, `.skel-w-64`, `.skel-h-sm` | **Token families added** (names encode the alpha, so a shade cannot drift): | Family | Members |
|---|---|
| Accent fill | `--accent-fill-4 -5 -7 -8 -10 -14 -16 -24 -30` |
| Accent line | `--accent-line-22 -28 -30 -40 -45 -48 -50 -55 -75 -85 -95` |
| Accent shades | `--accent-deep`, `--accent-mid`, `--accent-hover` |
| Ok ink | `--ok-ink`, `--ok-ink-strong`, `--ok-surface` |
| Ok fill / line | `--ok-fill-10 -13 -14 -16`, `--ok-line-40 -50 -70` |
| Bad ink | `--bad-ink`, `--bad-ink-soft`, `--bad-ink-strong`, `--bad-ink-deep`, `--bad-ink-warm`, `--bad-ink-mute`, `--bad-surface` |
| Bad fill / line | `--bad-fill-6 -10 -13`, `--bad-line-28 -35 -38 -45 -50` |
| Neutral ink | `--neutral-ink`, `--neutral-chev`, `--txt-ghost` |
| White lifts | `--white-1 -2 -3 -4 -5 -6 -7 -8 -9 -16 -22 -35 -45` |
| Scrims | `--scrim-25 -32 -45 -55 -62` |
| Surfaces | `--surface-panel-glass`, `--surface-soft-glass`, `--surface-state-run/-done/-fail`, `--surface-solid -2 -3 -4`, `--surface-thumb -2` |
| Lines | `--line-hover` | **Rule going forward:** a new colour, alpha, or radius literal in any stylesheet is a
defect. Extend the family instead. ---
## 4. Type
### Faces

`@font-face` ×4 at `web/fonts.css`; all self-hosted woff2 in `web/vendor/fonts`,
`font-display: swap`, variable weight ranges. | Role | Token | Family | Weight axis | Fallbacks |
|---|---|---|---|---|
| Display | `--font-display` | Fraunces | 300–700 variable | Iowan Old Style, Georgia, serif |
| Body | `--font-body` | Plex Sans | 400–700 variable | Segoe UI, system-ui, -apple-system, sans-serif |
| Mono | `--font-mono` | system monospace | — | Cascadia Code, Consolas | Preloaded: `fraunces-latin.woff2`, `plex-sans-latin.woff2` (`index.html:10-11`).
Latin-ext subsets ship and load through `unicode-range`.
### Base

`body { font: 15px/1.55 var(--font-body); }` (`web/layout.css body`).
### Ramp — every distinct size in use (no invented steps)

| Size | Selector | Weight / other |
|---|---|---|
| `clamp(27px,3vw,34px)` → `24px` @≤420 | `.view-head h1` | display 500, lh 1.12, ls `-.018em` |
| 21px | `.brand-mark` (K) | display 700, lh 1 |
| 19px | `.dz-title` | display 500 |
| 18px | `.brand-mark` @≤900 | display 700 |
| 17px | `.rh-name` | display 600, ls `-.01em` |
| 16px | `.brand-txt strong`, `.empty-title` | display 600 / 500 |
| 15px | `body`, `.staged-count`, `.card-title`, `.drawer-head` | display 600 for titles |
| 14px | `.settings-card-head` (600), `.extract-text`, `.nav-item`, `.view-head p`, `.btn`, `.input`, `.statusline`, `.field-val`, `.dz-mini`, `.hname` (550) | body |
| 13px | `.folder-label`, `.batch-bar`, `.toast`, `.dz-sub`, `.rh-desc`, `.chip`, `.sel-count`, `.prog-meta`, `.log-row`, `.empty-hint`, `.toast-act`, `.bulk-count`, `.side-foot` | body |
| 12px | `.mk-hint`, `.staged-summary`, `.rh-sub`, `.sig-legend`, `.seg-btn`, `.dz-mini-hint`, `.drawer-meta`, `.tc-name`, `.hsub`, `.hist-count`, `.log-row .lmsg`, `.set-hint`, `.brand-txt span` | meta |
| 11px | `.pill`, `.hgroup`, `.hsrc`, `.hbadge`, `.nav-group-label`, `.chip .n`, `.field-label` | labels; nav label 700; `.field-label` uppercase tracked |
| `.92em` | code inside `.set-hint` / `.view-head` | context-scoped |

Line-heights: `1` (brand-mark) · `1.12` (h1) · `1.2` (brand-txt) · `1.5`
(set-hint) · `1.55` (body, rh-desc, field-val) · `1.6` (textarea) · `1.7` (`.extract-text`). Letter-spacing: `-.018em` h1 · `-.01em` brand & rh-name · `.005em` card-title ·
`.02em` brand caption · `.04em` hgroup · `.11em` field-label · `.16em` kicker. **Verdict:** 6-step whole-pixel ramp (11 / 12 / 13 / 14 / 15 + display sizes). Half-pixel sizes normalised in 2026-11-11 pass.
`.kicker` removed. Still literal values, not tokenised.
`font-weight: 550` appears once (`.hname`, `web/components.css .hrow .ph`); valid because Plex Sans is
variable.

---

## 5. Colour semantics

| Meaning | Token | Where | Evidence |
|---|---|---|---|
| Primary action | `--accent` → `--accent-soft` gradient, ink `--accent-ink` | `.btn-primary`, active nav | `web/components.css .btn-primary` |
| Selected | `--accent` fill | `.thumb-card.is-sel`, `.tc-box` checked, `.seg-btn.is-on` | `web/components.css .thumb-card`, |
| Signal **kuat** | `--ok` dot + `rgba(86,192,139,.1)` fill | chips after Cek Google Suggest | `web/components.css .chip.sig-kuat`, legend |
| Signal **sedang** | `--accent` dot + `rgba(232,163,61,.1)` fill | chips | `web/components.css .chip.sig-sedang`, legend |
| Signal **lemah** | no dot, `opacity:.6` | chips and legend dot both use `--neutral-ink` | `web/components.css .chip.sig-lemah` |
| Signal **n/a** | dashed border, `opacity:.72` | chips where Google Suggest returned nothing | `web/components.css .chip.sig-na` |
| Success | `--ok` | done thumb overlay, `.pill.ok`, `.log-row.is-ok`, `.toast.is-ok` | `web/components.css .is-done`, |
| Failure | `--bad` | fail thumb, `.hbadge.bad`, `.statusline.is-bad`, `.toast.is-bad` | `web/components.css .is-fail`, |
| Over-limit tag (Etsy > 20 chars) | `--bad` tint | `.chip.is-over` | `web/components.css .chip.is-over` |
| Caution | `.pill.warn` amber tint | Etsy character counter pill | `web/components.css .pill.warn` |
| Copied | `--ok` flash | `.chip.is-copied` (`.rh-warn` carries the amber copy flash as `--accent-hover`) | `web/components.css .chip.is-copied`, `web/js/render.js` |
| Neutral meta | `--txt-faint` | hints, counts | throughout | Note: **`--warn` token ≡ `--accent`.** The UI's caution affordance is really "amber",
not a separate colour. Do not split them without a design decision.

---

## 6. Spacing

Declared scale in `web/tokens.css`. All steps are 4px multiples; the half-steps exist
only because real declarations needed them and a literal is the bigger sin. | Token | Value | Role |
|---|---|---|
| `--s1` | 4px | chip padding, copy-row top |
| `--s1h` | 5px | micro padding (seg button, chip note) |
| `--s1t` | 6px | in-card micro gap |
| `--s1q` | 7px | in-card gap: `.btn`, `.dz-full`, `.empty` |
| `--s2` | 8px | row gap, chip grid, icon gap |
| `--s2q` | 10px | toolbar row gap, sticky bars padding |
| `--s3` | 12px | section gap, card head padding |
| `--s3q` | 13px | dense row padding |
| `--s3h` | 14px | sidebar padding, legend gap |
| `--s3w` | 15px | heading padding, no-sidebar rows |
| `--s4` | 16px | block gap, panel body padding |
| `--s5` | 24px | view gap, shell padding |
| `--s6` | 32px | reserved (declared, not yet referenced) |
| `--s7` | 48px | reserved (declared, not yet referenced) | **Enforcement status:** every `gap` declaration in `web/components.css` and
`web/responsive.css` now reads from this scale. Most `padding` does too; the remaining
literals are one-off component dimensions (`44px 22px` empty state, `56px 26px`
dropzone, `18px` drawer body), not rhythm. ---
## 7. Radius, elevation, focus
### Radius in use

All radii are tokens now; no bare `px` radius remains in any stylesheet. | Token | Value | Where |
|---|---|---|
| `--radius-lg` | 20px | `.dropzone` |
| `--radius` | 14px | `.skel-*`, `.result-head`, `.card`, `.empty`, `.settings-card` |
| `--radius-md4` | 13px | `.staged-bar`, `.batch-bar`, `.dropzone.is-compact` |
| `--radius-md3` | 12px | `.thumb-card`, `.result-head img` |
| `--radius-md2` | 11px | `.statusline`, `.staged-bulk`, `.hrow`, `.bulkbar`, `.toast` |
| `--radius-md` | 10px | `.btn`, `.input`, `.nav-item` |
| `--radius-sm` | 9px | `.icon-btn`, `.seg`, `.log-row`, `.seg-btn` |
| `--radius-xs4` | 8px | `.dz-mini-ic`, `.tc-x`, `.hrow img`, `.hrow .ph` |
| `--radius-xs3` | 7px | `.chip`, `.toast-act`, inner seg button |
| `--radius-xs2` | 6px | `.tc-box`, `.skel-line` |
| `--radius-xs` | 5px | inline `code` |
| `--radius-pill` | 99px | `.pill`, `.hbadge`, `.hsrc`, progress bar, scrollbar thumb |
| 50% | circle | `.dz-icon`, `.empty-ico`, `.st-ic` |
| `var(--radius-md)` ×3 + 3px | asymmetric | `.brand-mark` at ≤900px (deliberate) | Top of the range is 20px on a full-width dropzone; no card or input exceeds 14px.
The oversized-radius ban is not violated.
### Elevation

| Value | Applied | Line |
|---|---|---|
| `--shadow`0 24px 60px -28px rgba(0,0,0,.9)` | `.staged-bar`, `.batch-bar`, `.drawer`, `.toast` | , |
| `0 8px 22px -10px rgba(232,163,61,.85)` | `.brand-mark` | |
| `0 10px 26px -14px rgba(232,163,61,.95), inset 0 1px 0 rgba(255,255,255,.35)` | `.btn-primary` | |
| `0 1px 0 rgba(255,255,255,.03) inset` | `.result-head` | |
| `0 0 0 1px var(--accent) inset, 0 10px 24px -18px rgba(232,163,61,.9)` | `.thumb-card.is-sel` | |
| `0 0 18px rgba(232,163,61,.45)` | `.progress .fill` | | Cards sit on 1px borders, not shadows — a consistent, deliberate choice
(`.card`).
### Focus

```css
:focus-visible { outline: none; box-shadow: var(--ring); } /* web/layout.css :focus-visible */
```

Two-layer ring: 2px page colour, then 4px amber at 75 %. Global. Secondary paths: `.dropzone:hover, .dropzone:focus-visible` also swaps border colour; `.tc-x:focus-visible` forces `opacity: 1`; `.input:focus` lifts border and background, while `.input:focus-visible` applies the full `var(--ring)`.

---

## 8. Components

Class inventory from `index.html` + `web/js/` markup against `web/components.css` selectors.
"States" lists implemented hooks; "Gap" lists reachable states with no styling. | Component | Selector | States | Gap |
|---|---|---|---|
| App shell | `.app` | desktop 248px + main | — |
| Sidebar | `.sidebar`, `.brand`, `.brand-mark`, `.brand-txt`, `.side-foot`, `.stat-row` | desktop, ≤900 icon bar | `backdrop-filter: blur(16px)` glass (see §12 item 5) |
| Nav group | `.nav-group`, `.nav-group-label`, `.nav-settings` | Keyword group, Extract group, Settings outside groups | labels hidden at ≤900; 11px sentence-case `--txt-faint` |
| Nav item | `.nav-item`, `.nav-item.is-active` | default / hover / active; history has `data-scope` keyword/extract | active uses a 3px left stripe (`web/layout.css .nav-item.is-active::before`) — side-stripe pattern |
| View head | `.view-head`, `h1`, `p` | static | `p` is 13.5px `--txt-faint`, `max-width 62ch` |
| Toolbar | `.toolbar`, `.spacer`, `.mk-label`, `.mk-hint` | wrap | `.mk-pick` in markup has **no CSS rule** |
| Button | `.btn` + `.btn-primary`.btn-ghost`.btn-danger-ghost`.btn.is-on` | default / hover / active / disabled / 4 variants | disabled = `opacity:.45` only (see §13 debt 4) |
| Icon button | `.icon-btn` | hover / disabled | disabled = `opacity:.4`, drawer variant `.3` |
| Input | `.input` | default / placeholder / focus | `::placeholder` uses `--txt-ghost` `#948a7a`; contrast re-measure pending browser pass |
| Textarea | `.input.textarea` | resizable, mono | — |
| Segmented | `.seg`, `.seg-btn`, `.seg-btn.is-on` | default / hover / on | — |
| Checkbox | `.check input`, `.hcheck input` | accent-coloured native | custom box only in `.tc-box` |
| Dropzone | `.dropzone`, `.is-drag`, `.is-compact`, `.dz-full`, `.dz-mini`, `.dz-icon`, `.dz-title`, `.dz-sub` | idle / hover+focus / drag / compact | single-image and extract share the pattern (multi-file, staging list); extract accepts PNG/JPG/WEBP/GIF/BMP |
| Status line | `.statusline`, `.is-bad` | idle / busy (spinner) / bad | — |
| Staged bar | `.staged-bar`, `.staged-count`, `.staged-summary` (`.s-done`, `.s-fail`), `.staged-bulk` | sticky, counts, selection bar | — |
| Progress | `.progress`, `.bar`, `.fill`, `.prog-meta` | scaleX tween `.35s` | compositor-only: `transform: scaleX()` on a full-width fill |
| Spinner | `.spinner`, `@keyframes spin` | infinite | — |
| Skeleton | `.skel-head`, `.skel-img`, `.skel-line`, `.skel-cards`, `.skel-card` | shimmer 1.5s | — |
| Results head | `.result-head`, `.rh-meta`, `.rh-name`, `.rh-sub`, `.rh-desc`, `.rh-actions`, `.dot` | static, ≤900 stack | `.dot` = middot separator |
| Cards | `.cards`, `.card`, `.is-lead`, `.card-head`, `.card-title`, `.card-body`, `.field-label`, `.field-val` | hover border, lead full-width | `transform` was removed from `transition`; hover is `border-color` only |
| Extract card | `.extract-card`, `.extract-text` | lead card, description prose plus attribute chip rows (`.attr-row`, `.chip.plain`, free-form values from AI), copy action; one card per staged image, stacked in `#ex-result` | no marketplace cards, no regenerate bar; staging grid reuses `.staged*` and `.thumb-card` from Generate |
| Pill | `.pill`, `.pill.ok`, `.pill.warn` | neutral / ok / warn | — |
| Chip | `.chip`, `.plain`, `.is-over`, `.is-checking`, `.is-copied`, `.sig-kuat`, `.sig-sedang`, `.sig-lemah`, `.sig-na`, `.n` | 9 states | `sig-sedang` shares the accent hue with a selected chip; disambiguated only by the dot |
| Signal legend | `.sig-legend`, `.lg.kuat/.sedang/.lemah` | 3 dots | weak dot uses `--neutral-ink` |
| Trends panel | `.trend-panel`, `.trend-head`, `.trend-intro`, `.trend-title`, `.trend-controls`, `.trend-field`, `.trend-terms`, `.trend-field-geo`, `.trend-status` | hidden/open, keyword + country form, `Buka Google Trends` link; status is `role="status" aria-live="polite"` | link opens `trends.google.com/trends/explore` in a new tab; no chart or API call |
| Empty state | `.empty`, `.empty-ico`, `.empty-title`, `.empty-hint` | 4 icons via `emptyHTML()` (`web/js/ui.js emptyHTML`) | — |
| Batch grid | `.batch-grid`, `.thumb-card`, `.tc-box`, `.tc-name`, `.tc-x`, `.tc-state`, `.st-ic` | default / hover / sel / running / done / fail / busy | — |
| Batch bar | `.batch-bar`, `.check`, `.sel-count` | sticky bottom, wrap | — |
| Batch log | `.batch-log`, `.log-row`, `.is-ok`, `.is-fail`, `.lname`, `.lmsg` | ok/fail | capped at 120 rows (`web/js/batch.js`) |
| History row | `.hrow`, `.is-sel`, `.is-nested`, `.hmeta`, `.hname`, `.hsub`, `.hbadge`.ok/.bad`, `.hchev`, `.hcheck`, `.hsrc` | hover / selected / nested under a batch header | no row-level focus style beyond the global ring |
| History list | `.history-list`, `.hgroup`, `.history-pager` | sticky date groups; keyword/extract scopes share the view; numbered pager (30 per page, `offset`) | `hgroup`top:0` collides with the ≤900 sticky sidebar; source filter and CSV export hidden for extract |
| Batch header row | `.hbatch`, `.hbatch-head`, `.hbatch-ico`, `.hbatch-name`, `.hbatch-meta`, `.hbatch-chev`, `.hbatch-list` | collapsed / expanded (`toggleBatch`) | nesting is visual order only (`order`), not `<ul>` nesting |
| History filter | `.hist-filter`, `.seg`, `.hist-count` | — | — |
| Bulk bar | `.bulkbar`, `.bulk-count` | shown/hidden | — |
| Settings | `.settings-form`, `.settings-card`, `.settings-card-head`, `.settings-card-body`, `.set-field`, `.set-row`, `.set-hint` (`.is-bad`), `.settings-actions`, `select.input` | static, error hint | `.set-row` becomes one column at ≤900 |
| Confirm dialog | `.confirm-wrap`, `.confirm`, `.confirm-x`, `.confirm-title`, `.confirm-desc`, `.confirm-input`, `.confirm-acts` | shown/hidden, `#confirm-ok:disabled` until the word `HAPUS` matches | in-app replacement for `confirm()`; still uses `role="dialog"` without focus trap |
| Drawer | `.drawer-wrap`, `.drawer-scrim`, `.drawer`, `.drawer-head`, `.drawer-body`, `.drawer-meta`, `.drawer-thumb` | open/close via Motion; **Buka gambar** opens `/api/history/{id}/image` in a new tab | full-resolution source, not the 320px thumbnail; focus trap + restore implemented (`drawerReturnFocus`, `trapFocus`) |
| Drawer action bar | `.drawer-act`, `.dact-mk`, `.dact-chip`, `.dact-chip.is-on`, `.dact-go` | sticky under `.drawer-head`, 5 marketplace chips, regenerate button disabled at 0 chips; hidden for extract runs | static position (not part of `.drawer-body` scroll), ≤560px wraps to 2 rows, button full width |
| Toast | `.toast`, `.show`, `.is-ok`, `.is-bad`, `.toast-act` | hidden/shown, ok/bad, undo button | timings 1.9 s / 3.2 s / 5.2 s (`web/js/core.js toast timings`); `.show` sets `pointer-events:auto` so `.toast-act` is clickable |
| Utilities | `[hidden]`, `.ellipsis`, `.spacer` | — | — | Dead CSS: `.kicker` rule was deleted — no markup or JS reference.
Missing CSS for markup: `.mk-pick`.
Tokens with zero references: `--warn`, `--radius-sm`, `--s1`, `--s2`, `--s6`, `--s7`.

---

## 9. Layout and responsive

```
.app            grid-template-columns: 248px 1fr; height: 100vh  (web/layout.css .app)
├── aside.sidebar   flex column, blur(16px), var(--s5) var(--s4) padding
└── main.main       overflow-y: auto; padding: 40px 44px 90px
    └── section.view   max-width: 1100px; margin: 0 auto
```

`body` carries two fixed radial gradients (amber at 8 % top-left, green at 100 % top-right, `body` radial gradients in `web/layout.css`) plus a fixed SVG noise overlay at `.05` opacity (`noise overlay in layout.css`). Both are part of the kraft texture; do not delete without a replacement texture.

Inner grids:

| Grid | Definition | Line |
|---|---|---|
| `.cards`, `.skel-cards` | `repeat(auto-fit, minmax(320px,1fr))` | |
| `.batch-grid` | `repeat(auto-fill, minmax(148px,1fr))` | |
| `.set-row` | `1fr 1fr` | |
| `.staged`, `.result-block`, `.results`, `.skel` | `display:grid; gap:var(--s4)` |

Exactly four media blocks:

| Query | Changes | Line |
|---|---|---|
| `(hover: none)` | staged × always visible | |
| `max-width: 900px` | shell → sticky horizontal icon bar; brand text + footer hidden; nav group labels hidden and groups flow inline; main padding `24px 18px 70px`; single-column cards; result head stacks and buttons stretch; `.input` flexes; `.set-row` one column; trend controls full width and fields flex; batch bar wraps | |
| `max-width: 420px` | h1 24px; dropzone `40px 18px`; toolbar buttons full width | |
| `max-width: 560px` | `.drawer-act` wraps: chips flow to 2 rows, `.dact-go` full width; trend panel padding tightens, run button full width, trend footer button loses auto margin | |
| `prefers-reduced-motion: reduce` | all animation/transition durations to `.001ms` | |

Wide screens: content is capped by `.view { max-width: 1100px }`, so a 1920px window shows a framed app rather than a stretched one. `html, body` have `height:100%` and no `overflow-x` guard — must be re-checked in the browser pass.

---

## 10. Motion

Library: Motion One, global `window.Motion`, loaded before `web/js/` (`index.html:314`). Optional — `const M = globalThis.Motion`, every call guarded (`web/js/core.js`).

| Use | Function | Values | Line |
|---|---|---|---|
| View transition in | `M.animate(view, {opacity:[0,1], transform:['translateY(8px)','none']})` | library defaults | `web/js/main.js` |
| Card stagger | `popStagger` | stagger per card | `web/js/ui.js popStagger` |
| Chip flash | `popChips` | scale pulse | `web/js/ui.js popChips` |
| Progress tween | `setFill` / `popProgress` | `transform: scaleX()` — no layout write | `web/js/ui.js setFill` |
| Drawer open | `M.animate` on `.drawer` + scrim | slide from right | `web/js/history.js drawer` |
| Drawer close | reverse | — | `web/js/history.js drawer` |

CSS-only motion:

| Effect | Definition | Line |
|---|---|---|
| Hover/active transitions | `.12s`–`.2s`, mostly `ease`, on `transform`, `background`, `border-color`, `color`, `opacity` | throughout |
| Spinner | `spin .7s linear infinite` | |
| Skeleton shimmer | `shimmer 1.5s ease-in-out infinite` on `background-position` | |
| Chip checking | `shimmer 1.1s linear infinite` | |
| Progress fill | `transform .35s ease`, `transform-origin: left center` | `web/components.css .progress .fill` |
| Toast | `opacity .2s, transform .2s` | |
| Button press | `translateY(1px) scale(.99)` | |

Reduced motion: CSS override (`web/responsive.css`) plus the `reduced` guard before every Motion call. Under reduced motion the spinner and shimmer stop (duration `.001ms`), which is acceptable for status feedback but means a long generation shows a static ring — the statusline text remains the real signal.

No animation touches `top`/`left`, and none animates a layout property. The progress fill is a full-width bar scaled with `transform: scaleX()`, so progression composites without relayout; the inline `width` update was removed in both progress bars (`popProgress` for batch, `setFill` for staged). Only the skeleton and chip-shimmer animate `background-position` (shimmer), which paints on the GPU.

---

## 11. Accessibility contract
### Present

| Item | Evidence |
|---|---|
| `lang="id"` on `<html>` | `index.html:2` |
| Global `:focus-visible` ring on every focusable element | `web/layout.css :focus-visible` |
| Chips are `<button>`, not styled `<span>` | `web/js/render.js` |
| History rows `role="button" tabindex="0"` with Enter/Space handlers | `web/js/history.js` |
| Dropzone keyboard-activatable (Enter/Space) | `web/js/upload.js` |
| Drawer keyboard steps ←/→/Escape | `web/js/history.js drawer` |
| Drawer focus trap: focus moves to `#drawer-close` on open, `Tab`/`Shift+Tab` cycle inside `FOCUSABLE`, focus restored to the opener on close | `web/js/history.js` `drawerReturnFocus`, `trapFocus`, `restoreFocus` — verified (Tab wraps last→`#drawer-prev`, Escape closes and returns focus to `#history-clear`) |
| Disabled states on all primary controls | `.btn:disabled`, `.icon-btn:disabled`, `.tc-x:disabled` |
| Signal state not colour-only (dot + border) | `web/components.css .chip.sig-*` |
| Reduced-motion honoured twice (CSS + JS) | `web/responsive.css`, `web/js/ui.js` |
| Toast carries its own action button, not a hidden click | `.toast-act`web/components.css .toast-act` |
| Native checkboxes keep OS semantics; accent colour only | `.check input`accent-color` |
| Trends status is a live region; keyword and country have id/name; the link opens a new tab with `rel="noopener"` | `web/js/trends.js` (`role="status" aria-live="polite"`, `#trend-terms`, `#trend-geo`) |
### Gaps

| Gap | Evidence | Severity |
|---|---|---|
| Drawer has no focus trap and no focus move on open; Tab escapes to the page behind the scrim | no `.focus()` anywhere in `web/js/`; `.drawer-wrap`web/components.css .drawer-wrap` | high — keyboard user can tab into hidden content |
| Confirm dialog has no focus trap and does not restore focus | `.confirm-wrap` in `index.html`, `wireConfirm()` in `web/js/history.js` | medium — same shape as the old drawer gap |
| Scaffold dialogs use `confirm()` / `alert()` rather than in-app modals | `web/js/settings.js` (history delete now uses the in-app `.confirm-wrap`) | medium — blocks the page, unstyled |
| Placeholder contrast fails AA: `#7c7264` on `rgba(0,0,0,.32)` over `--panel` ≈ 2.6:1 | `web/components.css .input::placeholder` | medium |
| Disabled controls convey state only via `opacity` (no `aria-disabled`, no colour) | | medium |
| `.hgroup` sticky `top:0` under the ≤900 sticky sidebar can overlap | `688` vs | low |
| No `aria-live` region for status line or toast | `web/js/core.js toast` sets text only | medium — screen reader misses completion |
| No landmark roles (`<nav>`, `<main>` are elements in markup; verify) | `index.html` | PASS — `<aside class="sidebar">`, `<nav class="nav">`, `<main class="main">`, `<header class="view-head">` present; drawer is `role="dialog" aria-modal="true"` |
| No skip link | not found | low |

---

## 12. Anti-slop floor

Sixteen items. Status is what the code shows today, not what it should show. | # | Item | Status | Evidence |
|---|---|---|---|
| 1 | No colour literals outside tokens | PASS | 0 literals outside `:root`, §3 |
| 2 | No animation of layout properties | PASS | `.progress .fill { transition: transform .35s }`, `scaleX()` driven by `setFill` / `popProgress` |
| 3 | No oversized radii on cards/inputs | PASS | max 20px on dropzone, 14px cards, §7 |
| 4 | No horizontal overflow | UNVERIFIED | no `overflow-x` guard; must render at 320 |
| 5 | No glassmorphism on core surfaces | **FAIL** | `.sidebar { backdrop-filter: blur(16px) }`web/layout.css .sidebar`; `.staged-bar`, `.batch-bar`blur(12px)` ; `.drawer-scrim`blur(3px)` |
| 6 | No gradient text | PASS | no `background-clip: text` |
| 7 | No radial blob decorations behind content | **FAIL (deliberate)** | `body` radial gradients `body radial gradients in layout.css` — part of the named texture direction; kept |
| 8 | No icon-in-a-tinted-circle as the only hierarchy | **FAIL** | `.dz-icon`web/components.css .dz-icon` (amber coin), `.empty-ico`web/components.css .empty-ico` (grey coin) |
| 9 | No uppercase tracked labels for section headings | **FAIL** | `.kicker` (rule already deleted), `.field-label`10.5px/.11em uppercase` |
| 10 | No middot separators in meta lines | **FAIL** | `.dot`web/components.css .dot`, used in `.rh-sub` |
| 11 | No pure black / pure white | **FAIL** | `#000` (icon font fallback), `#fff` (scrollbar thumb) |
| 12 | Type ramp uses whole steps | PASS | half-pixel steps normalised, §4 |
| 13 | No side-stripe accents on nav | **FAIL** | `.nav-item.is-active::before` 3px left stripe `web/layout.css .nav-item.is-active::before-171` |
| 14 | Every interactive element has hover / focus / disabled | **FAIL** | disabled-by-opacity on `.icon-btn`, `.tc-x`; `.input:focus` bypasses ring |
| 15 | No transition on `box-shadow` for focusable hover surfaces | UNVERIFIED | `.thumb-card` transitions `box-shadow`.15s`web/components.css .thumb-card`; focus ring is instant via `box-shadow` — measurable only in browser |
| 16 | Reduced motion respected | PASS | `web/responsive.css`, `web/js/ui.js` |

**Score: 5 PASS · 1 UNVERIFIED · 10 FAIL.** Items 5, 7, 8, 10, 13 are *intentional* parts of the "studio kraft" direction, not accidents — they are recorded as accepted deviations, not defects to remove blind. Items 1, 2, 11, 12, 14 are debt with no design justification.

---

## 13. Known drift and debt

**Fixed and verified in the stylesheet** (2026-11-10 token expansion):

| # | Debt |
|---|---|
| 1 | 124 colour literals outside `:root` - 0 remain |
| 3 | Input focus had no ring - `.input:focus` lifts border, `.input:focus-visible` adds `var(--ring)` |
| 9 | `--warn` removed; `--radius-sm` and the spacing scale are referenced again |
| 10 | `.card` transitions `border-color` only |
| 11 | Placeholder contrast: `--txt-ghost` raised from `#7c7264` to `#948a7a` (`web/tokens.css:16`) |
| 12 | `--s5` is 24px |
| 13 | Hand-copied token hexes replaced by tokens |
| 14 | JS-injected `#f6c76a` replaced by the `.rh-warn` class |
| 15 | `.progress .fill` animates `transform: scaleX()` — CSS, `popProgress`, `resetFill` and `setFill` (staged bar) all converted; verified in browser (25/70/100 %, no inline `width`) |
| - | Inline `style=` in skeleton markup moved to `.skel-*` classes |
| - | Bare `px` radii in `layout.css` tokenized |
| 6 | Drawer focus trap: focus to `#drawer-close` on open, `Tab` cycle inside `FOCUSABLE`, Escape + `restoreFocus()` on close (verified) |
| - | `.toast.show` `pointer-events:auto` — the Undo action was unclickable because the toast container stayed `pointer-events:none` |
| - | Batch stack fallback icon replaced by a real SVG (`.hbatch-ico`) instead of a 30px `!` glyph |
| - | `confirm()` replaced by the in-app `.confirm-wrap` dialog; `#confirm-ok` stays disabled until the typed word matches |
| - | CSV export honours the active filter (`export_runs(q, status, source)`)

**Open:**

| # | Debt | Where | Fix shape |
|---|---|---|---|
| 2 | Spacing migration ~60% done: literals such as `padding: 9px …`, `margin-top: 7px` remain | `web/components.css`, `web/layout.css` | finish substituting `--s*` |
| 4 | Disabled state = opacity only | `.btn:disabled`, `.icon-btn`, `.tc-x:disabled` | a disabled token/pattern + `aria-disabled` |
| 16 | Radius ladder over-granular: `--radius-xs…xs4` / `--radius-md…md4` fire 1-4x each | `web/tokens.css` | collapse to `sm` / `md` / `lg` / `pill` |
| 17 | Alpha families relocate rather than reduce magic numbers; `--accent-fill-30` and `--accent-line-30` are the same colour | `web/tokens.css` | keep the rule "line tokens for borders, fill tokens for backgrounds"; consider one `--accent-rgb` channel set |
| - | No browser verification | all views | pending the screenshot pass at 320/768/1280/1440 |

---

## 14. Applying this file

1. Every new UI rule must reuse a token from §3 or add one here first, with a role.
2. New spacing must use §6 (`--s4` is the workhorse). If a literal is unavoidable, record it in §6's off-grid row.
3. New colours must extend §5 semantics, not invent a hue.
4. New components get a row in §8 with their selector and states.
5. A change that flips a §12 item flips this file in the same commit.
6. `docs/DESIGN.md` is authoritative over any skill. When `hallmark` or `refactoring-ui` says something that contradicts a token here, this file wins.
