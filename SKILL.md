---
name: uigate
description: Lints local HTML/CSS for measurable UI defects and AI-template tells -- WCAG contrast ratios computed from literal colors (4.5:1 normal / 3:1 large), missing :focus-visible styles, missing/empty img alt text, interactive targets below 40px, text below 12px, plus labeled slop heuristics (purple-indigo gradients, Inter-only stacks, card grids, emoji headings, hero boilerplate, hardcoded palettes). Use when shipping a landing page, in CI on every PR that touches markup/styles, or when a page starts looking like the same AI slop. Exit 1 = a fail rule fired (or any warning with --strict); exit 2 = no HTML/CSS files / bad usage.
license: MIT
compatibility: Requires Python 3.8+ stdlib only -- no dependencies, no network, no JS execution. Pure static parse (html.parser + regex). Works in Claude Code, Codex, Cursor, and any Agent Skills compatible client.
metadata:
  author: F0Rextasy
  version: "1.0"
---

# uigate

The UI stops looking like the same AI slop: every finding prints a
measured value next to its threshold, so the fix is arithmetic, not
taste. Contrast ratios, pixel sizes, missing selectors -- printed, not
vibed.

## The one rule

You may not ship a page with a measurable defect:

```bash
python scripts/uigate . --strict
```

- **exit 1** - a failure-class rule fired (or any warning with
  `--strict`).
- **exit 0** - the UI is clean.
- **exit 2** - usage: no HTML/CSS files, bad `--allow`, unreadable file.

## Protocol

1. **Point at a file or directory**: uigate reads `.html`/`.htm`/`.css`
   (a directory without any is a usage error - there is nothing to
   gate).
2. **Objective pass** (fail): contrast, focus, alt, targets, text size.
3. **Slop-tell pass** (warn, disclosed heuristics): gradients, fonts,
   card grids, emoji headings, hero boilerplate, hardcoded palettes.
4. **Read findings** as
   `file:line  FAIL  rule  measured  [threshold T]`, then fix or exempt:
   `--allow RULE=reason` (repeatable), counted in the summary and JSON.

## Rules

| Rule | Severity | Fires when |
| --- | --- | --- |
| `low-contrast` | fail | literal color pair below 4.5:1 (normal) or 3:1 (large text) |
| `missing-focus-style` | fail | page CSS with no `:focus` selector anywhere |
| `missing-alt` | fail | `<img>` without `alt`, or with empty `alt` |
| `small-target` | fail | literal interactive size below 40px |
| `small-text` | fail | `font-size` below 12px |
| `ai-gradient` | warn | >=2 stops from the published purple-indigo template palette |
| `system-font-only` | warn | `Inter`/`system-ui` stack with no custom face |
| `card-grid` | warn | >=3 identical `border-radius` **and** >=3 identical `box-shadow` |
| `emoji-heading` | warn | emoji inside `<h1>`/`<h2>` |
| `hero-boilerplate` | warn | `get started` / `unlock the power of` / `supercharge your` / `lorem ipsum` |
| `hardcoded-palette` | warn | >=3 literal colors, zero `var(` references |

```console
$ python scripts/uigate examples/red/index.html --no-color  # excerpt; full run: 10 failures, 10 warnings
index.html:8   FAIL  low-contrast         2.85:1  [threshold 4.5:1]  #999999 on #ffffff -- raise the contrast (darker text, lighter background, or larger type)
index.html:1   FAIL  missing-focus-style  0 focus selectors  [threshold >=1 (:focus-visible)]  no :focus rule in page CSS -- add a :focus-visible rule so keyboard users can see where they are
index.html:28  FAIL  missing-alt          no alt attribute  [threshold non-empty alt]  <img> without alt text -- write a non-empty alt describing the image (decorative images should be CSS backgrounds, not <img>)
index.html:30  FAIL  small-target         32px  [threshold min 40px]  <button> target 32px is not tappable -- grow the target to at least 40x40px so it is tappable
index.html:10  FAIL  small-text           11px  [threshold min 12px]  font-size 11px renders below readable minimum -- grow body copy to at least 12px

uigate: 10 failure(s), 10 warning(s) across 1 file(s) checked
uigate: fix the UI -- or exempt a rule with:  --allow RULE=<reason>
[exit 1]
```

## Reporting back

1. Counts: failures / warnings / files checked.
2. Every finding: file, line, rule, measured value, threshold.
3. Command and exit code.
