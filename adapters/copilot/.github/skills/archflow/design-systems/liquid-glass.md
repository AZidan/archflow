---
name: liquid-glass
label: Apple HIG — Liquid Glass
platforms:
  ios_swiftui: SwiftUI
  ipados_swiftui: SwiftUI
  macos_swiftui: SwiftUI
  ios_uikit: UIKit
  macos_appkit: AppKit
---

# Apple HIG — Liquid Glass

Apple's current design language across iOS 26, iPadOS 26, macOS Tahoe 26, watchOS 26 and tvOS 26.
Its organising idea is a strict separation into two layers: a **content layer** that owns the
information and scrolls freely, and a **controls layer** that floats above it made of Liquid Glass
— a dynamic material that refracts, reflects and reacts to whatever passes beneath it, and that
adapts its own contrast to stay legible. Navigation bars, tab bars, toolbars, sidebars and
floating action controls live in that glass layer; everything else stays in the opaque content
layer. Corners are concentric with the hardware and with their containers, and every colour,
type size and material is a system semantic that adapts to light mode, dark mode, accessibility
settings and the wallpaper behind it. This system is **Apple platforms only** — it depends on
system materials that cannot be honestly reproduced on the web, and must never be selected for a
web target.

## Signature traits

- **Two layers, never blended.** Content scrolls in the opaque layer; controls float in the glass
  layer. Glass is never placed on glass.
- **The material is dynamic, not a blur.** It refracts and reflects the content moving under it
  and re-tunes its own contrast; it is not a static translucent panel you can imitate with a
  fixed blur radius and opacity.
- **Concentric corner radii.** A control nested inside a container gets a radius derived from the
  container's, so curves stay parallel — not an arbitrary matched number.
- **Everything is semantic.** `Color.primary`, `.secondary`, `.tint`, `.background`; Dynamic Type
  text styles; SF Symbols. No literal colours, no literal point sizes.
- **Content extends under the chrome.** Scroll views run edge to edge beneath the floating bars,
  handled by scroll-edge effects rather than by insetting the content away from them.

## Platforms and libraries

| Platform | Library / framework | Theme entry point |
|---|---|---|
| iOS / iPadOS | SwiftUI (iOS 26+) | `.tint()` on the root view; system semantic colours |
| iOS / iPadOS (legacy) | UIKit (iOS 26+) | `UIGlassEffect`, `tintColor` on the window |
| macOS | SwiftUI (macOS 26+) | `.tint()`, `NSGlassEffectView` for AppKit interop |
| macOS (legacy) | AppKit (macOS 26+) | `NSGlassEffectView`, `NSAppearance` |
| watchOS / tvOS | SwiftUI | system-provided; glass is applied by the platform chrome |

## Setup

**SwiftUI** — nothing to install; the system frameworks ship with the SDK. Build against the
iOS 26 / macOS 26 SDK so the standard components adopt Liquid Glass automatically. The whole
app's accent is one line at the root: `.tint(Color("BrandAccent"))`, with the colour defined as
a *colour set* in the asset catalog carrying both Any and Dark appearances. Light and dark are
therefore free — never branch on `colorScheme` to pick a colour.

Custom glass surfaces use `.glassEffect(.regular, in: .rect(cornerRadius: …))`, and multiple
adjacent glass elements must be wrapped in a single `GlassEffectContainer` so they merge and
morph as one material rather than stacking.

**UIKit** — apply `UIGlassEffect` through a `UIVisualEffectView`; for AppKit use
`NSGlassEffectView` / `NSGlassEffectContainerView`. Prefer the standard bar and toolbar classes,
which adopt the material without any per-view work.

## Component vocabulary

Use these names in wireframes, DSL files and handoffs.

| Generic term | SwiftUI | UIKit / AppKit |
|---|---|---|
| Screen container | `NavigationStack` / `NavigationSplitView` | `UINavigationController` / `NSSplitViewController` |
| Header / nav bar | `.navigationTitle` + `.toolbar { ToolbarItem }` | `UINavigationBar` + `UINavigationItem` |
| Large title header | `.navigationBarTitleDisplayMode(.large)` | `prefersLargeTitles` |
| Tab bar | `TabView` + `Tab` | `UITabBarController` |
| Side navigation | `NavigationSplitView` sidebar / `TabView(.sidebarAdaptable)` | `UISplitViewController` |
| Search | `.searchable(text:)` | `UISearchController` |
| Primary button | `Button` + `.buttonStyle(.glassProminent)` | `UIButton.Configuration.prominentGlass()` |
| Secondary button | `Button` + `.buttonStyle(.glass)` | `UIButton.Configuration.glass()` |
| Low-emphasis action | `Button` + `.buttonStyle(.plain)` | `UIButton.Configuration.plain()` |
| List | `List` | `UICollectionView` (list layout) |
| List item | `NavigationLink` / `LabeledContent` row in `List` | `UICollectionViewListCell` |
| Grouped section | `Section` with `.listStyle(.insetGrouped)` | list configuration `.insetGrouped` |
| Card / grouped panel | `GroupBox` or a `Section` | `UIView` + background configuration |
| Modal | `.sheet` + `.presentationDetents` | `UIViewController` modal + `UISheetPresentationController` |
| Confirmation | `.alert` / `.confirmationDialog` | `UIAlertController` |
| Popover / menu | `Menu` / `.popover` | `UIMenu` / `UIPopoverPresentationController` |
| Form field | `TextField` / `SecureField` inside `Form` + `Section` | `UITextField` |
| Selection control | `Toggle` / `Picker` / `Stepper` | `UISwitch` / `UISegmentedControl` |
| Floating action | `.toolbar` item, or a glass `Button` over content | glass `UIButton` above the content view |
| Progress | `ProgressView` | `UIActivityIndicatorView` / `UIProgressView` |
| Icon | `Image(systemName:)` (SF Symbols) | `UIImage(systemName:)` |
| Pull-to-refresh | `.refreshable` | `UIRefreshControl` |
| Swipe actions | `.swipeActions` | `UISwipeActionsConfiguration` |

## Layout, spacing, and type scale

- **Grid:** 8pt rhythm; 4pt for tight optical adjustments only. Standard content margin is 16pt
  on iPhone, 20pt on iPad regular width.
- **Spacing steps:** 4, 8, 12, 16, 20, 24, 32. Prefer the system default — `VStack { }` with no
  explicit spacing, and `.padding()` with no argument — over a hand-picked number.
- **Safe areas are law.** Nothing interactive outside them; content may extend under bars, and
  the scroll-edge effect handles legibility.
- **Corner radii:** concentric with the container. A control inset by `p` inside a container of
  radius `R` gets radius `R − p`. Free-floating glass controls use `.capsule` or the container
  shape.
- **Touch targets:** 44×44pt minimum on iOS; 28pt minimum click targets on macOS.
- **Type styles:** `largeTitle`, `title`, `title2`, `title3`, `headline`, `subheadline`, `body`,
  `callout`, `footnote`, `caption`, `caption2`. Body copy is `.body`. All must scale with Dynamic
  Type — the layout is verified at the AX5 setting before a screen is considered done.

## Rules

- **Glass never stacks on glass.** One material layer. Adjacent glass elements go inside one
  `GlassEffectContainer`.
- **No custom colours in code.** Semantic colours (`.primary`, `.secondary`, `Color(.systemBackground)`)
  or asset-catalog colour sets with light and dark appearances. `Color(red:green:blue:)` and hex
  helpers in a view are violations.
- **No custom point sizes.** `.font(.body)`, not `.font(.system(size: 17))`.
- **Do not tint or restyle the glass material.** Set the app's accent once with `.tint()` and let
  the material respond. Custom fills, gradients or opacities over glass are violations.
- **Use the standard components.** A hand-built navigation bar or tab bar forfeits the material,
  the scroll-edge effect and the accessibility behaviour that come free with the real ones.
- **Icons are SF Symbols**, with the weight and scale matching the adjacent text style.
- **Honour accessibility settings.** Reduce Transparency, Increase Contrast, Reduce Motion and
  Dynamic Type all change the rendering; never hardcode around them.
- **No custom components unless a gap is logged** in `design-artifacts/component-gaps.md` with
  the HIG section it falls outside of.

## Anti-patterns

A review fails if any of these appear.

- A hand-rolled blur — `UIVisualEffectView` with `.systemUltraThinMaterial` plus a manual
  overlay, a `.background(.ultraThinMaterial)` stack, or a fixed-opacity white panel — used to
  imitate glass instead of `.glassEffect` / `UIGlassEffect`.
- Glass on glass: a `.glassEffect` view placed inside another glass surface, or two sibling glass
  views outside a `GlassEffectContainer`.
- Literal colours or literal font sizes in a view body.
- A branch on `@Environment(\.colorScheme)` to select a colour that an asset-catalog colour set
  should have handled.
- Material Design carried over: a floating circular FAB, a hamburger drawer, a bottom
  `NavigationBar` built by hand, filled rectangular buttons with elevation, Material Symbols
  instead of SF Symbols.
- A custom back button, or a navigation bar built from an `HStack` instead of `.toolbar`.
- Content inset away from the bars with manual padding rather than allowed to scroll beneath them.
- Fixed-height rows or containers that clip at larger Dynamic Type sizes.
- `.frame(width:height:)` on text, hardcoded to a size that only works at the default setting.
- Any use of this system in a web, Android, Flutter or React Native target.

## Examples

See `examples/liquid-glass/` — login, list and detail screens showing the two-layer structure,
the floating glass chrome and concentric radii:

- `examples/liquid-glass/login.png`
- `examples/liquid-glass/list.png`
- `examples/liquid-glass/detail.png`

They are visual references only. Write SwiftUI from the framework's own types; the screenshots
were produced with a web approximation and must not be transcribed.
