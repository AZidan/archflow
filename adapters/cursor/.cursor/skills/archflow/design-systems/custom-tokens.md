---
name: custom-tokens
label: Custom / match my brand
platforms:
  web_react: "headless (Radix Primitives) + tokens.json"
  web_next: "headless (Radix Primitives) + tokens.json"
  web_vue: "headless (Ark UI) + tokens.json"
  web_components: "headless (Zag.js) + tokens.json"
  react_native: "headless (RN primitives) + tokens.json"
  flutter: "flutter ThemeData from tokens.json"
  android_compose: "Compose MaterialTheme from tokens.json"
  ios_swiftui: "SwiftUI theme struct from tokens.json"
  ipados_swiftui: "SwiftUI theme struct from tokens.json"
  macos_swiftui: "SwiftUI theme struct from tokens.json"
  ios_uikit: "UIKit appearance proxies from tokens.json"
  macos_appkit: "AppKit NSAppearance from tokens.json"
  windows_winui: "WinUI ResourceDictionary from tokens.json"
---

# Custom / match my brand

The brand-agnostic option: instead of adopting someone else's visual language, the project
defines its own in a single `tokens.json` and builds components on top of a **headless**
primitive library that supplies behaviour and accessibility but no styling. Every colour,
space, size, radius, shadow, font and duration in the product traces back to one entry in that
file, in three tiers — primitives (raw values), semantics (roles like `surface.default`,
`text.muted`, `action.primary`), and component tokens (`button.primary.bg`). Screens reference
only semantics and component tokens, so a rebrand, a dark theme, or a white-label tenant is a
change to `tokens.json` and nothing else. Choose this when a brand already exists and must be
matched exactly, when the product will be themed per customer, or when no off-the-shelf system
fits. It costs more up front than Material or Fluent and pays back on the second theme.

## Signature traits

- **One source of truth.** `tokens.json` is the design system; the code is a projection of it.
- **Three tiers, strictly.** Primitive → semantic → component. Screens may only read the top two.
- **Headless behaviour, owned styling.** Radix / Ark / Zag give focus management, keyboard
  handling and ARIA; every pixel is yours.
- **Themes are data.** Light, dark and per-tenant themes are alternate value sets over the same
  semantic keys — never duplicated components.
- **Generated, not hand-copied.** A build step turns `tokens.json` into CSS variables, a Dart
  `ThemeData`, a Compose theme or a Swift struct, so no platform drifts.

## Platforms and libraries

| Platform | Headless base | Theme entry point |
|---|---|---|
| Web (React / Next) | `@radix-ui/react-*` primitives (+ Tailwind or vanilla-extract) | CSS custom properties on `:root` / `[data-theme]` |
| Web (Vue / Solid / Svelte) | Ark UI | same |
| Web components / framework-free | Zag.js | same |
| React Native | RN primitives + `react-native-reanimated` | a `ThemeProvider` context |
| Flutter | Flutter widgets, unstyled | `ThemeData` + a `ThemeExtension` carrying the tokens |
| Android (Compose) | Compose Foundation | `MaterialTheme` with a custom `CompositionLocal` token set |
| iOS / iPadOS / macOS (SwiftUI) | SwiftUI primitives | a `Theme` struct injected via `@Environment` |
| iOS / macOS (UIKit / AppKit) | UIKit / AppKit controls, restyled | appearance proxies / `NSAppearance` |
| Windows (WinUI) | WinUI controls, restyled | `ResourceDictionary.ThemeDictionaries` |

## Setup

1. **Create `design-artifacts/tokens.json`.** Use the starter below, or point Archflow at an
   existing export (Figma variables, Style Dictionary, a Tailwind config) and let it be
   normalised into this shape. The path is recorded as `theme.brand_tokens` in
   `.archflow/design-system.yaml`.

2. **Add a build step** that emits platform artefacts from it. `style-dictionary` is the usual
   choice on web and cross-platform projects:
   ```
   npm i -D style-dictionary
   npx style-dictionary build      # → src/styles/tokens.css, tokens.dart, Tokens.swift, ...
   ```
   The generated files are committed but never edited by hand — regenerate instead.

3. **Mount the theme once at the root** — a `:root` CSS block on web, a `ThemeProvider` in RN,
   `ThemeData` in Flutter, an `@Environment` value in SwiftUI. Alternate themes swap the value
   set only.

4. **Install the headless base** for the platform from the table above and build the component
   set in `components/ui/`, one component per file, styled entirely from component tokens.

**Starter `tokens.json`** (`generate` in the picker writes exactly this, with the brand ramp
seeded from the colour you supply):

```json
{
  "primitive": {
    "color": {
      "brand":   { "50":"", "100":"", "200":"", "300":"", "400":"", "500":"", "600":"", "700":"", "800":"", "900":"" },
      "neutral": { "0":"#ffffff", "50":"", "100":"", "200":"", "300":"", "400":"", "500":"", "600":"", "700":"", "800":"", "900":"", "1000":"#000000" },
      "success": { "500":"" }, "warning": { "500":"" }, "danger": { "500":"" }
    },
    "space":  { "0":"0", "1":"4px", "2":"8px", "3":"12px", "4":"16px", "5":"24px", "6":"32px", "7":"48px", "8":"64px" },
    "radius": { "none":"0", "sm":"4px", "md":"8px", "lg":"12px", "xl":"16px", "full":"9999px" },
    "font":   { "family": { "sans":"", "mono":"" },
                "size":   { "xs":"12px", "sm":"14px", "md":"16px", "lg":"20px", "xl":"24px", "2xl":"32px", "3xl":"40px" },
                "weight": { "regular":"400", "medium":"500", "semibold":"600", "bold":"700" },
                "leading":{ "tight":"1.2", "normal":"1.5", "loose":"1.7" } },
    "shadow": { "sm":"", "md":"", "lg":"" },
    "motion": { "duration": { "fast":"120ms", "base":"200ms", "slow":"320ms" },
                "easing":   { "standard":"cubic-bezier(.2,0,0,1)", "emphasized":"cubic-bezier(.3,0,0,1)" } }
  },
  "semantic": {
    "light": {
      "surface":  { "default":"{primitive.color.neutral.0}", "raised":"{primitive.color.neutral.50}", "sunken":"{primitive.color.neutral.100}", "overlay":"" },
      "text":     { "default":"{primitive.color.neutral.900}", "muted":"{primitive.color.neutral.600}", "inverse":"{primitive.color.neutral.0}", "onAction":"" },
      "border":   { "default":"{primitive.color.neutral.200}", "strong":"{primitive.color.neutral.400}", "focus":"{primitive.color.brand.500}" },
      "action":   { "primary":"{primitive.color.brand.600}", "primaryHover":"{primitive.color.brand.700}", "secondary":"", "disabled":"" },
      "feedback": { "success":"", "warning":"", "danger":"" }
    },
    "dark": { "surface": {}, "text": {}, "border": {}, "action": {}, "feedback": {} }
  },
  "component": {
    "button":  { "primary": { "bg":"{semantic.action.primary}", "fg":"{semantic.text.onAction}", "radius":"{primitive.radius.md}", "paddingX":"{primitive.space.4}", "height":"40px" } },
    "input":   { "bg":"{semantic.surface.default}", "border":"{semantic.border.default}", "radius":"{primitive.radius.md}", "height":"40px" },
    "card":    { "bg":"{semantic.surface.raised}", "border":"{semantic.border.default}", "radius":"{primitive.radius.lg}", "padding":"{primitive.space.5}" },
    "modal":   { "bg":"{semantic.surface.default}", "radius":"{primitive.radius.xl}", "shadow":"{primitive.shadow.lg}" }
  }
}
```

Every key in `semantic.light` must have a counterpart in `semantic.dark`. Empty strings in the
starter are the values to fill from the brand.

## Component vocabulary

The project's own component names, built on the headless base. Use these names in wireframes,
DSL files and handoffs, and keep the file names in `components/ui/` identical.

| Generic term | Component name | Headless base (React) |
|---|---|---|
| Header / app bar | `AppHeader` | — (composed) |
| Tab bar / tabs | `Tabs` / `TabList` / `TabPanel` | `@radix-ui/react-tabs` |
| Side navigation | `SideNav` / `SideNavItem` | — (composed) |
| Breadcrumbs | `Breadcrumbs` / `BreadcrumbItem` | `@radix-ui/react-navigation-menu` |
| Primary button | `Button` (`variant="primary"`) | `@radix-ui/react-slot` |
| Secondary button | `Button variant="secondary"` | — |
| Low-emphasis action | `Button variant="ghost"` | — |
| Destructive action | `Button variant="danger"` | — |
| Card / panel | `Card` / `CardHeader` / `CardBody` / `CardFooter` | — |
| List item | `ListRow` (+ `ListRowLeading` / `ListRowTrailing`) | — |
| Data table | `DataTable` | `@tanstack/react-table` |
| Modal | `Modal` / `ModalHeader` / `ModalBody` / `ModalFooter` | `@radix-ui/react-dialog` |
| Side panel | `Panel` | `@radix-ui/react-dialog` |
| Confirmation | `ConfirmDialog` | `@radix-ui/react-alert-dialog` |
| Popover / menu | `Popover` / `Menu` / `MenuItem` | `@radix-ui/react-popover`, `-dropdown-menu` |
| Form | `Form` / `FormField` / `FormLabel` / `FormError` | `react-hook-form` + `zod` |
| Form field | `TextInput` / `TextArea` / `Select` / `Checkbox` / `RadioGroup` / `Toggle` | `@radix-ui/react-select`, `-checkbox`, `-radio-group`, `-switch` |
| Transient message | `Toast` / `useToast` | `@radix-ui/react-toast` |
| Inline message | `Banner` | — |
| Status pill | `Tag` | — |
| Loading | `Skeleton` / `Spinner` | — |
| Avatar | `Avatar` | `@radix-ui/react-avatar` |
| Tooltip | `Tooltip` | `@radix-ui/react-tooltip` |

## Layout, spacing, and type scale

- **Grid:** 4px base. Spacing only from `primitive.space` (0, 4, 8, 12, 16, 24, 32, 48, 64).
- **Radii:** only from `primitive.radius`. Components reference the component-tier token
  (`card.radius`), not the primitive.
- **Type scale:** only from `primitive.font.size` — xs 12 · sm 14 · md 16 · lg 20 · xl 24 ·
  2xl 32 · 3xl 40, with the three weights and three line-heights defined. Body copy is `md` on
  mobile, `sm` in dense desktop UI.
- **Elevation:** three shadow steps, mapped to resting card / popover / modal. Nothing else.
- **Motion:** two easings and three durations; every transition names one of each.
- **Breakpoints:** define them once in `tokens.json` and reference by name — never inline
  media-query widths.
- **Touch targets:** 44px minimum on touch platforms, 32px on pointer-only desktop.

## Rules

- **Three tiers, one direction.** Components read component tokens; component tokens read
  semantics; semantics read primitives. A component referencing a primitive directly
  (`primitive.color.brand.600`) is a violation — add a semantic for it instead.
- **Nothing enters the UI that is not in `tokens.json` first.** A new colour, spacing step or
  radius is added to the file and regenerated before it can be used.
- **Never edit generated theme files.** Change `tokens.json` and rebuild.
- **Both themes always.** Every semantic key exists in `light` and `dark` before a screen ships.
- **Behaviour comes from the headless base.** Do not reimplement focus traps, roving tabindex,
  dismiss handling or ARIA — wrap the primitive.
- **Contrast is verified, not assumed.** Every text-on-surface and text-on-action pair meets
  WCAG AA (4.5:1 body, 3:1 large text and UI boundaries) in both themes; record the check in
  `design-artifacts/contrast-report.md`.
- **One component per file in `components/ui/`,** named exactly as in the vocabulary table.
- **New components are logged** in `design-artifacts/component-gaps.md` with the token additions
  they required.

## Anti-patterns

A review fails if any of these appear.

- A hex, `rgb()`, `hsl()` or named colour literal anywhere outside `tokens.json`.
- A hardcoded spacing, radius, font size, shadow or duration value in a component:
  `padding: 13px`, `borderRadius: 10`, `fontSize: 15`, `transition: 250ms`.
- A component reading a primitive token where a semantic should exist — the sign that the
  semantic tier is being skipped.
- Dark mode implemented by duplicated components, a `isDark ?` ternary in a view, or a second
  stylesheet, rather than an alternate value set.
- A generated tokens file edited by hand.
- A styled component library (MUI, Chakra, Ant, Bootstrap) installed alongside — it brings a
  second, competing theme system.
- A dialog, dropdown, tooltip or tab set hand-built from divs and `useState` instead of the
  headless primitive: no focus trap, no escape handling, no ARIA.
- Semantic keys present in `light` but missing in `dark`.
- Media queries with inline pixel widths instead of the named breakpoints.
- One-off component tokens invented at a call site rather than added to `tokens.json`.
- Text or icon colours chosen without a recorded contrast check.

## Examples

See `examples/custom-tokens/` — login, list and detail screens rendered from the starter token
set, showing the three-tier structure applied to a neutral brand:

- `examples/custom-tokens/login.png`
- `examples/custom-tokens/list.png`
- `examples/custom-tokens/detail.png`

They demonstrate structure and token discipline, not a target aesthetic — the brand's own
`tokens.json` supplies the look.
