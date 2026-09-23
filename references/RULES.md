# UI rule catalogue

Input: one HTML/CSS file or a directory tree. Missing path -> usage
error (exit 2); a directory with no `.html`/`.htm`/`.css` files ->
usage error too (nothing to lint is not a clean verdict). External
stylesheet links resolve relative to the HTML file on disk; remote
(`://`), `data:` and `#` hrefs are skipped; unreadable files are usage
errors, never silently dropped.

Parser: stdlib `html.parser` for page structure plus regex over
`<style>` blocks, linked stylesheets, and `style=""` attributes. CSS
comments are masked before brace matching so commented braces cannot
desync rule line numbers, and all values are read from the original
text. Unknown values (`var()`, relative units, percentages we cannot
resolve) are skipped, never guessed.

## Objective rules (fail)

| Rule | Condition |
| --- | --- |
| `low-contrast` | literal `color` against literal `background-color`/`background` (bare page defaults to `#ffffff`) with WCAG 2.1 relative-luminance ratio below 4.5:1 (normal text) or 3:1 (large text: `>=24px`, or `>=18.66px` with bold `>=700`) |
| `missing-focus-style` | a page/stylesheet with CSS but no `:focus` selector anywhere (`:focus-visible` satisfies it) |
| `missing-alt` | `<img>` with no `alt` attribute, or an `alt` that is empty/whitespace |
| `small-target` | `<button>`, `<a>`, `<input>` (non-hidden), `<select>`, `<textarea>` whose smallest literal `width`/`height` (px or unitless in `style=""`/attributes) is below 40px; unmeasurable targets are skipped |
| `small-text` | a `font-size` in `px`/`pt` (pt converted at 96/72) below 12px |

## Slop-tell rules (warn, disclosed heuristics)

| Rule | Condition |
| --- | --- |
| `ai-gradient` | a single declaration value whose color stops include >=2 of the published template palette `#6366f1 #8b5cf6 #a855f7 #d946ef #7c3aed #4f46e5` |
| `system-font-only` | a `font-family` mentioning `inter` or `system-ui` with no `@font-face` and no font-bearing `<link>` |
| `card-grid` | >=3 identical `border-radius` values **and** >=3 identical `box-shadow` values across the page (inline styles included) |
| `emoji-heading` | an emoji-range character inside an `<h1>`/`<h2>` (entities unescaped before matching) |
| `hero-boilerplate` | a text line containing `get started`, `unlock the power of`, `supercharge your`, or `lorem ipsum` (case-insensitive) |
| `hardcoded-palette` | >=3 literal colors (`#hex`/`rgb()`) and zero `var(` references in page CSS |

## Exit codes

| Code | Meaning |
| --- | --- |
| 0 | no failing rule; no warning under `--strict` |
| 1 | a fail rule fired, or any warning with `--strict` |
| 2 | usage: missing path, no HTML/CSS files, non-HTML/CSS file target, bad `--allow`, unreadable file |

## Invariants

- Findings are a pure function of the file bytes; same input, same
  rows, same exit code, on every OS.
- Every finding prints `file  line  rule  measured_value  threshold`:
  the contrast ratio, the pixel size, the missing selector -- measured,
  never vibes.
- Row order is deterministic: per-file alphabetical by rule, then line,
  then measured value.
- The tells are labeled heuristics, not taste verdicts: the
  contrast/alt/focus/target rules cite WCAG reference numbers, the
  tells cite the exact token that fired.
