---
name: material3
label: Material 3
platforms:
  flutter: flutter_material
  android_compose: androidx.compose.material3
  web_react: "@mui/material"
  web_vue: vuetify
---

# Material 3

Google's current design language (also called Material You). It is a token-driven system built
around a *seed color*: one brand color generates five tonal palettes, and every surface, text
colour and state colour in the app is a role drawn from those palettes — so light mode, dark
mode and Android's dynamic wallpaper colour all fall out of one definition. Surfaces separate by
tonal tint rather than heavy shadow, corners are generously rounded, and the type scale is
expressive with large display and headline roles. Best for Android apps, Flutter apps on any
target, and web products that want a familiar, accessible, highly-themable look without inventing
a system from scratch. It is the safest default when a project has no strong brand opinion yet.

## Signature traits

- **Seed-generated colour.** One `seedColor` produces the whole `ColorScheme`; components never
  name a colour, they name a role (`primary`, `onPrimary`, `surfaceContainerHigh`, `error`).
- **Tonal elevation.** Depth reads as a tinted surface (`surfaceContainerLowest` → `Highest`),
  not as a drop shadow. Shadows are reserved for genuinely floating elements.
- **A shape scale.** Corner radii come from a named scale (none / extra-small 4 / small 8 /
  medium 12 / large 16 / extra-large 28 / full) — components pick a step, never an arbitrary px.
- **Four-tier button hierarchy.** Filled → Filled-tonal → Outlined → Text, in descending emphasis.
  At most one Filled button per screen region.
- **Expressive, role-based type.** Display / Headline / Title / Body / Label, each in Large,
  Medium and Small — no ad-hoc font sizes.

## Platforms and libraries

| Platform | Library / package | Theme entry point |
|---|---|---|
| Flutter | Flutter SDK `material` (`flutter_material`) | `ThemeData(colorScheme: ColorScheme.fromSeed(...))` |
| Android native | `androidx.compose.material3` | `MaterialTheme(colorScheme = ...)` |
| Web (React) | `@mui/material` v6+ | `<ThemeProvider theme={createTheme(...)}>` |
| Web (Vue) | `vuetify` v3 | `createVuetify({ theme: { ... } })` |

## Setup

**Flutter** — no dependency needed, `material` ships with the SDK:
```
ThemeData(useMaterial3: true, colorScheme: ColorScheme.fromSeed(seedColor: <brand>))
```
passed to `MaterialApp(theme:, darkTheme:, themeMode:)`. Define both schemes with
`ColorScheme.fromSeed(..., brightness: Brightness.dark)`.

**Android / Compose** — add `androidx.compose.material3:material3` and `material3-window-size-class`.
Wrap the app in `MaterialTheme(colorScheme = dynamicColorScheme(context) ?: fallbackScheme)`.
Prefer dynamic colour on Android 12+; always supply a static fallback.

**React** — `npm i @mui/material @emotion/react @emotion/styled`. Build the theme once in
`src/theme.ts` with `createTheme({ colorSchemes: { light, dark } })` and mount a single
`<ThemeProvider>` plus `<CssBaseline />` at the app root.

**Vue** — `npm i vuetify`; register the plugin with a `theme` block defining `light` and `dark`.

## Component vocabulary

Use these names in wireframes, DSL files and handoffs. Never write a generic term where a
system name exists.

| Generic term | Flutter | Compose | MUI (React) |
|---|---|---|---|
| Header / nav bar | `AppBar` | `TopAppBar` (`Small`/`Medium`/`Large`/`CenterAligned`) | `AppBar` + `Toolbar` |
| Tab bar (bottom) | `NavigationBar` + `NavigationDestination` | `NavigationBar` + `NavigationBarItem` | `BottomNavigation` |
| Tabs (in-page) | `TabBar` + `Tab` | `TabRow` + `Tab` | `Tabs` + `Tab` |
| Side navigation | `NavigationRail` / `NavigationDrawer` | `NavigationRail` / `ModalNavigationDrawer` | `Drawer` |
| Primary button | `FilledButton` | `Button` | `Button variant="contained"` |
| Secondary button | `FilledButton.tonal` | `FilledTonalButton` | `Button variant="contained" color="secondary"` |
| Tertiary button | `OutlinedButton` | `OutlinedButton` | `Button variant="outlined"` |
| Low-emphasis action | `TextButton` | `TextButton` | `Button variant="text"` |
| Floating action | `FloatingActionButton` | `FloatingActionButton` | `Fab` |
| List item | `ListTile` | `ListItem` | `ListItem` + `ListItemButton` |
| Card | `Card` (`filled`/`elevated`/`outlined`) | `Card` / `ElevatedCard` / `OutlinedCard` | `Card` |
| Modal dialog | `AlertDialog` / `Dialog` | `AlertDialog` / `BasicAlertDialog` | `Dialog` |
| Bottom sheet | `showModalBottomSheet` | `ModalBottomSheet` | `Drawer anchor="bottom"` |
| Form field | `TextField` (`OutlineInputBorder`) | `OutlinedTextField` / `TextField` | `TextField variant="outlined"` |
| Selection control | `Checkbox` / `Radio` / `Switch` | same | same |
| Chip / filter | `FilterChip` / `InputChip` / `AssistChip` | same | `Chip` |
| Transient message | `SnackBar` | `Snackbar` + `SnackbarHost` | `Snackbar` |
| Progress | `CircularProgressIndicator` / `LinearProgressIndicator` | same | `CircularProgress` / `LinearProgress` |

## Layout, spacing, and type scale

- **Grid:** 4dp base unit; lay out on an 8dp rhythm. Screen edge margin 16dp on compact,
  24dp on medium+.
- **Spacing steps:** 4, 8, 12, 16, 24, 32, 48. Nothing between them.
- **Shape scale:** none 0 · extra-small 4 · small 8 · medium 12 · large 16 · extra-large 28 · full.
- **Elevation levels:** 0, 1, 2, 3, 4, 5 — expressed as `surfaceContainer*` tint first, shadow
  only for FAB, menus and dialogs.
- **Touch targets:** 48×48dp minimum, always.
- **Type roles:** `displayLarge/Medium/Small`, `headlineLarge/Medium/Small`,
  `titleLarge/Medium/Small`, `bodyLarge/Medium/Small`, `labelLarge/Medium/Small`.
  Body copy is `bodyLarge` (16sp) on mobile. Buttons use `labelLarge`.
- **Window size classes:** compact < 600dp, medium 600–839dp, expanded ≥ 840dp. Navigation
  changes with the class: `NavigationBar` → `NavigationRail` → permanent drawer.

## Rules

- **No hardcoded colours.** Every colour is a `ColorScheme` role. `Colors.blue`, `#6750A4`,
  `theme.palette.grey[300]` in a component are all violations. Change the seed, not the widget.
- **No arbitrary radii.** Pick a step from the shape scale.
- **No arbitrary font sizes.** Pick a type role. `fontSize: 15` is a violation.
- **One Filled button per region.** Everything else is tonal, outlined or text.
- **Contrast pairs are fixed.** Content on `primary` uses `onPrimary`; on `surfaceVariant` uses
  `onSurfaceVariant`. Never mix roles across pairs.
- **No third-party component libraries** alongside the Material implementation. If a needed
  component genuinely does not exist, compose it from Material primitives and log the gap in
  `design-artifacts/component-gaps.md` with the reason.
- **Dark mode is not optional.** Both `ColorScheme`s are defined before the first screen ships.
- **Icons come from Material Symbols** (`Icons.*` in Flutter, `@mui/icons-material` on web).

## Anti-patterns

A review fails if any of these appear.

- Hex literals, `Color(0xFF...)`, `Colors.*` constants, or Tailwind-style colour classes inside a
  component instead of a `ColorScheme` role.
- A custom `BoxShadow` / `boxShadow` / `elevation` value not from the elevation levels, used to
  fake depth that tonal surfaces should provide.
- Corner radii like `borderRadius: 10` / `6px` that are not on the shape scale.
- Explicit `fontSize` / `fontWeight` on a `Text` instead of a `textTheme` role.
- iOS conventions transplanted in: a back chevron with a text label, a bottom sheet used where a
  dialog belongs, an iOS-style segmented control, `Cupertino*` widgets in a Material tree.
- Two or more Filled/contained buttons competing in the same view.
- A second UI kit in the dependency list (Chakra, Ant, Bootstrap, GetWidget) alongside Material.
- Ripple / state-layer disabled to "clean up" interaction feedback.
- Hand-rolled `Container` + `GestureDetector` where `ListTile`, `Card` or a Button exists.
- Touch targets under 48dp, or an icon button with no `tooltip` / `contentDescription`.

## Examples

See `examples/material3/` — login, list and detail screens rendered with Material 3 colour,
shape and type tokens:

- `examples/material3/login.png`
- `examples/material3/list.png`
- `examples/material3/detail.png`

They are visual references for spacing, hierarchy and component choice. Write code from the
library's own types — do not transcribe the markup that produced these screenshots.
