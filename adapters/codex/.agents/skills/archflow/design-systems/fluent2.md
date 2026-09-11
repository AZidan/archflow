---
name: fluent2
label: Fluent 2
platforms:
  web_react: "@fluentui/react-components"
  web_components: "@fluentui/web-components"
  windows_winui: WinUI 3
---

# Fluent 2

Microsoft's design system, the language of Windows 11, Microsoft 365, Teams and Azure. It is
built for dense, productive, information-heavy software: compact controls, a restrained neutral
ramp with a single brand ramp of sixteen shades, small radii, and depth expressed through a
graduated shadow scale plus Windows materials (Mica on window backgrounds, Acrylic on transient
surfaces). Everything is addressed through named design tokens rather than values, so a theme
swap — light, dark, high contrast, or a customer's brand ramp — is a provider prop. Best for
Windows desktop apps, enterprise web tools, admin consoles and anything that must sit
comfortably beside Microsoft 365.

## Signature traits

- **Token-addressed, never value-addressed.** `tokens.colorNeutralForeground1`,
  `tokens.spacingHorizontalM`, `tokens.borderRadiusMedium` — no literals anywhere.
- **A brand ramp of 16.** One brand colour is expanded into `brand10`…`brand160`; components
  select ramp positions, so rebranding is one ramp definition.
- **Dense and compact.** Small default control heights (32px), 4px grid, small radii (4/6/8),
  tight vertical rhythm — designed for screens with a lot on them.
- **Graduated depth.** `shadow2` / `shadow4` / `shadow8` / `shadow16` / `shadow64` map to
  interaction depth (resting card → flyout → dialog), not to taste.
- **Appearance props, not variants of your own.** `appearance="primary" | "outline" | "subtle" |
  "transparent"` recurs across the control set.

## Platforms and libraries

| Platform | Library / package | Theme entry point |
|---|---|---|
| Web (React) | `@fluentui/react-components` v9 | `<FluentProvider theme={webLightTheme}>` |
| Web (any framework) | `@fluentui/web-components` v3 | `setTheme()` + design tokens |
| Windows desktop | WinUI 3 (Windows App SDK) | `Application.Resources` theme dictionaries |
| Icons | `@fluentui/react-icons` | — |

## Setup

**React**
```
npm i @fluentui/react-components @fluentui/react-icons
```
Wrap the app root in exactly one `<FluentProvider theme={webLightTheme}>`, switching to
`webDarkTheme` from the user's preference. For a brand, generate a ramp with
`createLightTheme(brandRamp)` / `createDarkTheme(brandRamp)` and pass those instead. Styling is
Griffel: `const useStyles = makeStyles({ root: { color: tokens.colorNeutralForeground1 } })`,
consumed as `const styles = useStyles()`. Never write inline style objects with literal values.

**Web components** — import the components you use and call `setTheme(webLightTheme)` once.

**WinUI 3** — reference the Windows App SDK; controls pick up Fluent automatically. Theme through
`ResourceDictionary.ThemeDictionaries` (Light / Dark / HighContrast) and reference brushes by key
(`{ThemeResource TextFillColorPrimaryBrush}`), never by literal colour.

## Component vocabulary

Use these names in wireframes, DSL files and handoffs.

| Generic term | Fluent UI React v9 | WinUI 3 |
|---|---|---|
| Header / app bar | `Toolbar` + `ToolbarButton` | `CommandBar` / custom title bar |
| Tab bar / tabs | `TabList` + `Tab` | `TabView` + `TabViewItem` |
| Side navigation | `NavDrawer` + `NavItem` / `NavCategory` | `NavigationView` + `NavigationViewItem` |
| Breadcrumbs | `Breadcrumb` + `BreadcrumbItem` + `BreadcrumbDivider` | `BreadcrumbBar` |
| Primary button | `Button appearance="primary"` | `Button` with `AccentButtonStyle` |
| Secondary button | `Button` (default) | `Button` |
| Tertiary button | `Button appearance="outline"` | `Button` |
| Low-emphasis action | `Button appearance="subtle"` / `"transparent"` | `HyperlinkButton` |
| Split / menu button | `SplitButton` / `MenuButton` | `SplitButton` / `DropDownButton` |
| Card / panel | `Card` + `CardHeader` + `CardPreview` + `CardFooter` | `Expander` / bordered `Grid` |
| List item | `List` + `ListItem` | `ListView` + `ListViewItem` |
| Data table | `DataGrid` (`DataGridHeader`/`Row`/`Cell`) or `Table` | `ItemsView` / `DataGrid` |
| Tree | `Tree` + `TreeItem` | `TreeView` |
| Modal | `Dialog` + `DialogSurface` + `DialogBody` + `DialogTitle` + `DialogActions` | `ContentDialog` |
| Side panel | `Drawer` (`OverlayDrawer` / `InlineDrawer`) | `SplitView` pane |
| Popover / menu | `Popover` / `Menu` + `MenuTrigger` + `MenuPopover` + `MenuItem` | `Flyout` / `MenuFlyout` |
| Form field | `Field` wrapping `Input` / `Textarea` / `Dropdown` / `Combobox` | `TextBox` + `Header` |
| Selection control | `Checkbox` / `RadioGroup` + `Radio` / `Switch` | `CheckBox` / `RadioButtons` / `ToggleSwitch` |
| Transient message | `Toaster` + `useToastController` + `Toast` | `InfoBar` (transient) |
| Inline message | `MessageBar` + `MessageBarBody` | `InfoBar` |
| Status pill | `Badge` / `CounterBadge` | `InfoBadge` |
| Loading | `Spinner` / `ProgressBar` / `Skeleton` | `ProgressRing` / `ProgressBar` |
| Avatar | `Avatar` / `AvatarGroup` | `PersonPicture` |
| Tooltip | `Tooltip` | `ToolTipService` |
| Icon | `@fluentui/react-icons` (`*Regular` / `*Filled`) | Segoe Fluent Icons |

## Layout, spacing, and type scale

- **Grid:** 4px base unit. Page padding `spacingHorizontalXXL` (24px); section gaps
  `spacingVerticalL` (16px); control gaps `spacingHorizontalS` (8px).
- **Spacing tokens:** `XXS 2 · XS 4 · SNudge 6 · S 8 · MNudge 10 · M 12 · L 16 · XL 20 ·
  XXL 24 · XXXL 32`, in `spacingHorizontal*` and `spacingVertical*` forms.
- **Radius tokens:** `borderRadiusSmall 2 · Medium 4 · Large 6 · XLarge 8 · Circular`.
  Controls use Medium; cards and dialogs use Large or XLarge.
- **Shadow tokens:** `shadow2` resting card · `shadow4` hover · `shadow8` popover/menu ·
  `shadow16` drawer · `shadow64` dialog. Each has a `*Brand` variant.
- **Control heights:** small 24 · medium 32 (default) · large 40.
- **Type ramp:** `caption2 · caption1 · body1 · body1Strong · body2 · subtitle2 · subtitle1 ·
  title3 · title2 · title1 · largeTitle · display`, applied via `tokens.fontSizeBase300` etc. or
  the `Text` component's `size`/`weight` props. Body copy is `body1` (14px). Font family is
  `tokens.fontFamilyBase` (Segoe UI Variable on Windows, with the system fallback stack elsewhere).
- **Materials (Windows):** Mica on the window background, Acrylic on flyouts and transient
  surfaces. Never simulate them with a static translucent fill.

## Rules

- **One `FluentProvider` at the root**, and exactly one. Nested providers are only for a
  deliberately scoped sub-theme (e.g. an embedded dark panel).
- **Style with `makeStyles` + `tokens` only.** No inline `style={{ color: '#0078D4' }}`, no
  literal px in a Griffel rule where a spacing token exists.
- **Never mix v8 and v9.** `@fluentui/react` (v8) and `@fluentui/react-components` (v9) in the
  same tree produce two conflicting theme systems.
- **Use `appearance` props** rather than inventing variants. One `appearance="primary"` button
  per view region.
- **Every input is wrapped in `Field`** so label, hint, validation state and required marker are
  wired correctly.
- **Icons come from `@fluentui/react-icons`** (or Segoe Fluent Icons on WinUI), Regular for
  resting and Filled for selected states.
- **High contrast is a supported theme**, not an afterthought — verify with
  `teamsHighContrastTheme` / the Windows high-contrast dictionaries.
- **No custom components unless a gap is logged** in `design-artifacts/component-gaps.md`.

## Anti-patterns

A review fails if any of these appear.

- A hex literal in a component — `#0078D4`, `#faf9f8`, `rgba(0,0,0,.08)` — instead of a token.
- Literal pixel values for spacing, radius or shadow where `tokens.spacing*`,
  `tokens.borderRadius*` or `tokens.shadow*` exist.
- v8 (`@fluentui/react`) imports alongside v9, or `office-ui-fabric-react` anywhere.
- A second UI kit (MUI, Bootstrap, Ant) in `package.json` beside Fluent.
- Material or Bootstrap conventions carried in: a circular FAB, a bottom navigation bar, large
  pill-shaped primary buttons, `rounded-full` cards, Material Icons.
- `Tabs` or a nav rebuilt from divs where `TabList` / `NavDrawer` exist.
- A bare `<input>` or an `Input` without a `Field` wrapper, so the label is only a placeholder.
- Radii of 10, 12 or 16px on controls — off-ramp for Fluent's compact geometry.
- Acrylic or Mica faked with a fixed-opacity overlay, or applied to a resting window background
  where Mica belongs.
- Custom `box-shadow` values, or shadows used on resting list rows.
- Control heights other than 24 / 32 / 40, or touch targets under 32px on a touch-capable target.

## Examples

See `examples/fluent2/` — login, list and detail screens showing Fluent's density, neutral ramp,
token-driven spacing and shadow scale:

- `examples/fluent2/login.png`
- `examples/fluent2/list.png`
- `examples/fluent2/detail.png`

Visual references only. Write code from the library's own types and tokens.
