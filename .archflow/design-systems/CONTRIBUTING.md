# Adding a design system

A design system is a single plain markdown file in this directory. It is **not** a skill and
**not** a command — nothing loads it by description matching. Agents read it deterministically:
`.archflow/design-system.yaml` names it, and every UI-producing agent is told to
"read and follow `.archflow/design-systems/<name>.md`".

To add one, copy the template below to `<name>.md`, fill it in, and mirror the file into
`.archflow/design-systems/` (this repository keeps the shipped plugin tree and its own dogfood
copy identical).

## Requirements

- **File name** is the system's id: lowercase, kebab-case, matching the `name` in the
  frontmatter and the value written into `design_system:` in `.archflow/design-system.yaml`.
- **Under 300 lines.** These files are read into agent context on every UI task.
- **No component code samples.** Naming tables, rules and constraints only — agents write code
  from the library's own types. A theme entry-point snippet or a token file is fine; a rendered
  `<Button>` implementation is not.
- **All nine sections, in this order, with these exact headings.** Commands and agents index
  into them by heading.
- **Frontmatter is required.** The picker in `/archflow:design` filters by the `platforms` map
  without parsing prose, so a system is offered on exactly the platforms listed there. Omitting
  a platform key is how a system is kept off that platform — Liquid Glass has no `web_*` key,
  which is what prevents it ever being offered for a web target.

### Platform ids

Use only these. Add a new id here first if a genuinely new target is needed.

`flutter` · `android_compose` · `ios_swiftui` · `ipados_swiftui` · `macos_swiftui` ·
`ios_uikit` · `macos_appkit` · `react_native` · `web_react` · `web_next` · `web_vue` ·
`web_components` · `windows_winui`

## Template

````markdown
---
name: <kebab-case-id>            # must equal the filename
label: <Display Name>            # shown in the picker
platforms:                       # platform id → the concrete library/package for that platform
  web_react: "<npm package>"     # this value becomes `library:` in .archflow/design-system.yaml
  flutter: <package>
---

# <Display Name>

One paragraph. What the system looks and feels like, who it is for, and which platforms it fits.
This is the only part shown to the user in the picker, so it has to be enough to choose on.
End it with the situation where this system is the right call — and, if the system is restricted
(platform-locked, licence-bound), say so explicitly here.

## Signature traits

3–5 bullets. What makes output recognisably *this* system rather than a generic app. Prefer
structural traits (how colour is derived, how depth is expressed, how variants are named) over
adjectives.

## Platforms and libraries

| Platform | Library / package | Theme entry point |
|---|---|---|
| … | … | … |

One row per key in the frontmatter `platforms` map — the table and the frontmatter must agree.

## Setup

Install command and the theming entry point per library. Where the theme is defined, what wraps
the app root, and how light/dark is declared. Keep it to what an agent needs to bootstrap the
project correctly.

## Component vocabulary

| Generic term | <Library A> | <Library B> |
|---|---|---|
| Header / nav bar | … | … |
| Tab bar / tabs | … | … |
| Side navigation | … | … |
| Primary button | … | … |
| Secondary button | … | … |
| Low-emphasis action | … | … |
| Card / panel | … | … |
| List item | … | … |
| Data table | … | … |
| Modal | … | … |
| Popover / menu | … | … |
| Form | … | … |
| Form field | … | … |
| Selection control | … | … |
| Transient message | … | … |
| Inline message | … | … |
| Status pill | … | … |
| Loading | … | … |
| Icon | … | … |

Cover at least the rows above. Agents must use these names in wireframes, DSL files and
handoffs, so every generic term a designer might write needs a mapping — including the ones the
system does *not* have (say so in a Notes column rather than leaving the row out).

## Layout, spacing, and type scale

The grid and base unit, the allowed spacing steps, the radius scale, the elevation/shadow scale,
minimum touch targets, and the named type roles. Be specific enough that "is this value on the
scale?" has a yes/no answer.

## Rules

Hard constraints, as imperatives. At minimum cover: where colour may come from, where sizes and
radii may come from, whether dark mode is mandatory, which icon set, whether a second UI library
is allowed, and the gap-logging path (`design-artifacts/component-gaps.md`) for anything the
system genuinely lacks.

## Anti-patterns

Open with "A review fails if any of these appear." Then list concrete, checkable violations —
what off-system output actually looks like, not principles. The QA and code-review agents run
this section as a mandatory checklist, so each bullet must be something a reviewer can point at
in a diff.

Include the cross-system contamination cases: which *other* system's conventions most often leak
into this one, and what they look like.

## Examples

See `examples/<name>/` — login, list and detail screens:

- `examples/<name>/login.png`
- `examples/<name>/list.png`
- `examples/<name>/detail.png`
````

## Examples

Each system has `examples/<name>/` holding three screenshots — `login.png`, `list.png`,
`detail.png` — plus the `login.html` / `list.html` / `detail.html` and shared `theme.css` they
were captured from. All five systems render the same imaginary app ("Fieldnote", a fieldwork task
tracker) so the screenshots are directly comparable.

**The screenshots are the reference. The HTML is not a code sample** — it is a web approximation
used purely to produce the images, including for the native systems, and must never be
transcribed into a project. Agents write code from the real library's own types.

Each page is sized to its own viewport, so the capture is the full page with no cropping:

| Systems | Viewport |
|---|---|
| `material3`, `liquid-glass` | 390 × 844 (phone) |
| `shadcn`, `fluent2`, `custom-tokens` | 1200 × 800 (desktop) |

To regenerate, from inside `examples/<name>/`:

```bash
CH="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"   # or your Chrome path
for s in login list detail; do
  "$CH" --headless --disable-gpu --hide-scrollbars --force-device-scale-factor=2 \
    --window-size=<W>,<H> --screenshot="$PWD/$s.png" "file://$PWD/$s.html"
done
```

## Checklist before opening a PR

- [ ] Filename, frontmatter `name`, and the id used everywhere else all match
- [ ] `platforms` map lists only ids from the list above, and matches the section 3 table
- [ ] All nine headings present, in order, spelled exactly as in the template
- [ ] Under 300 lines
- [ ] No component code samples
- [ ] `## Anti-patterns` bullets are all checkable in a diff
- [ ] `examples/<name>/` has all three screenshots
- [ ] File mirrored into `.archflow/design-systems/` identically
