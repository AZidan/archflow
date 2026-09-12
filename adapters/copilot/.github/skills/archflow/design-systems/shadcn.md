---
name: shadcn
label: shadcn/ui
platforms:
  web_react: shadcn/ui
  web_next: shadcn/ui
---

# shadcn/ui

Not a component library you install, but a collection of components you copy into your own
repository and then own. Behaviour and accessibility come from Radix UI primitives; every visual
decision is Tailwind CSS driven by a small set of CSS custom properties (`--background`,
`--foreground`, `--primary`, `--radius`) that define light and dark themes in one place.
The default look is deliberately restrained: a near-neutral greyscale, one accent colour, tight
letter-spacing on headings, small type, subtle borders instead of shadows. Because the source
lives in your `components/ui/` folder there is no upgrade treadmill and no fighting a library's
opinions — you edit the component. Best for React and Next.js products, internal tools,
dashboards and marketing sites where a clean modern default and full control both matter.

## Signature traits

- **You own the source.** Components are added by CLI into `components/ui/` and are yours to edit.
- **Semantic CSS variables, not palette classes.** Components reference `bg-background`,
  `text-muted-foreground`, `bg-primary` — never `bg-slate-900`. Dark mode is the `.dark` class
  re-declaring the same variables.
- **Radix underneath.** Focus management, keyboard nav, portals and ARIA are inherited, not
  reimplemented.
- **Variants via `cva`.** Every component's looks are enumerated in a
  `class-variance-authority` config and merged with `cn()` (clsx + tailwind-merge).
- **Quiet by default.** Borders and low-contrast surfaces do the separating; shadows are small
  and reserved for overlays.

## Platforms and libraries

| Platform | Library / package | Theme entry point |
|---|---|---|
| Web (React + Vite) | `shadcn/ui` (Radix + Tailwind) | `app.css` / `index.css` `:root` and `.dark` variable blocks |
| Web (Next.js) | `shadcn/ui` | `app/globals.css` `:root` and `.dark` blocks |
| Forms | `react-hook-form` + `zod` + `@hookform/resolvers` | `Form` wrapper component |
| Icons | `lucide-react` | — |
| Charts | `recharts` via the `chart` component | `ChartContainer` config |

## Setup

```
npx shadcn@latest init          # writes components.json, tailwind config, CSS variables, cn()
npx shadcn@latest add button card dialog form input table tabs
```

`init` creates `components.json` (the project's style, base colour, path aliases and whether CSS
variables are used — always yes) and writes the theme into the app's global stylesheet as two
blocks: `:root` for light and `.dark` for dark. Changing the brand means editing those variables
and `--radius`, nothing else. Dark mode is toggled by putting `.dark` on `<html>`; use
`next-themes` in Next.js.

Every subsequent component is added with `npx shadcn@latest add <name>` — never hand-copied from
the docs site, and never installed from npm.

## Component vocabulary

Use these names in wireframes, DSL files and handoffs.

| Generic term | shadcn/ui component | Notes |
|---|---|---|
| Header / app bar | custom `<header>` + `NavigationMenu` | shadcn ships no app bar; compose one |
| Tab bar / tabs | `Tabs` + `TabsList` + `TabsTrigger` + `TabsContent` | |
| Side navigation | `Sidebar` (`SidebarProvider`, `SidebarMenu`, `SidebarTrigger`) | |
| Breadcrumbs | `Breadcrumb` + `BreadcrumbItem` | |
| Primary button | `Button` (default variant) | one per view region |
| Secondary button | `Button variant="secondary"` | |
| Tertiary button | `Button variant="outline"` | |
| Low-emphasis action | `Button variant="ghost"` / `variant="link"` | |
| Destructive action | `Button variant="destructive"` | |
| Card / panel | `Card` + `CardHeader` + `CardTitle` + `CardDescription` + `CardContent` + `CardFooter` | |
| List item | a `Card`, a `Table` row, or a div pair separated by `Separator` | no `ListItem` exists |
| Data table | `Table` + `TableHeader`/`TableRow`/`TableCell`, with `@tanstack/react-table` | |
| Modal | `Dialog` + `DialogContent` + `DialogHeader` + `DialogFooter` | |
| Side panel | `Sheet` | |
| Mobile bottom panel | `Drawer` (vaul) | |
| Confirmation | `AlertDialog` | destructive confirmations only |
| Popover / menu | `Popover` / `DropdownMenu` / `ContextMenu` | |
| Command palette | `Command` / `CommandDialog` | |
| Form | `Form` + `FormField` + `FormItem` + `FormLabel` + `FormControl` + `FormMessage` | always with react-hook-form + zod |
| Form field | `Input` / `Textarea` / `Select` / `Checkbox` / `RadioGroup` / `Switch` | inside `FormControl` |
| Combobox | `Popover` + `Command` | there is no single `Combobox` |
| Transient message | `Sonner` (`toast()`) | `Toast` is deprecated |
| Inline message | `Alert` + `AlertTitle` + `AlertDescription` | |
| Status pill | `Badge` | |
| Loading | `Skeleton` | prefer over spinners for content |
| Avatar | `Avatar` + `AvatarImage` + `AvatarFallback` | |
| Tooltip | `Tooltip` + `TooltipTrigger` + `TooltipContent` | |

## Layout, spacing, and type scale

- **Grid:** Tailwind's 4px scale. Use `gap-*` and `space-y-*`, not margins on children.
- **Spacing steps:** `1 2 3 4 6 8 12 16` (4–64px). Arbitrary values like `p-[13px]` are violations.
- **Radius:** everything derives from `--radius`. `rounded-lg` on cards and dialogs,
  `rounded-md` on buttons and inputs, `rounded-full` on avatars and badges.
- **Type:** base is `text-sm` (14px) for UI, `text-base` for prose. Headings are
  `text-3xl font-semibold tracking-tight` (page), `text-xl font-semibold` (section),
  `text-sm font-medium` (label). Secondary copy is `text-sm text-muted-foreground`.
- **Page shell:** `container mx-auto` with `px-4 md:px-6 lg:px-8`; content max-width around
  `max-w-6xl` for dashboards, `max-w-2xl` for forms and prose.
- **Borders:** `border` + `border-border`. One hairline is usually enough — do not add a shadow
  as well.

## Rules

- **Add components with the CLI.** `npx shadcn@latest add <component>` — never npm-install a
  shadcn package, never paste from the docs by hand.
- **Only semantic colour classes.** `bg-background`, `bg-card`, `bg-primary`,
  `text-foreground`, `text-muted-foreground`, `border-border`, `bg-destructive`. Palette classes
  (`bg-slate-50`, `text-zinc-500`) and hex values in components are violations.
- **Never write `dark:` colour variants.** Dark mode is handled by the `.dark` variable block. A
  `dark:bg-gray-900` in a component means the theme was bypassed.
- **New variants go in `cva`**, in the component file, not as conditional class strings at call
  sites. Merge classes with `cn()` so `className` overrides still win.
- **Forms use `Form` + react-hook-form + zod.** A bare `<input>` with `useState` is a violation.
- **Do not break the Radix composition.** Keep `Trigger`/`Content`/`Portal` structure intact;
  extra wrapper divs between them break focus and ARIA wiring.
- **Icons are `lucide-react`**, sized `h-4 w-4` beside `text-sm` text.
- **No second UI library.** If a component is genuinely missing, build it from Radix + Tailwind
  in `components/ui/` and log it in `design-artifacts/component-gaps.md`.

## Anti-patterns

A review fails if any of these appear.

- A raw `<button className="bg-blue-600 text-white rounded px-4 py-2">` where `Button` exists.
- Palette colour classes or hex literals in a component: `bg-slate-900`, `text-[#111]`,
  `border-gray-200`.
- `dark:` colour utilities anywhere outside the global CSS variable blocks.
- Arbitrary Tailwind values for spacing, radius or size: `p-[13px]`, `rounded-[7px]`,
  `text-[15px]`.
- MUI, Chakra, Ant Design, react-bootstrap or DaisyUI in `package.json` alongside shadcn.
- Editing a component inside `node_modules`, or importing from a `shadcn-ui` npm package.
- An uncontrolled `<input>` + `useState` form instead of `Form`/`FormField`, or validation done
  by hand instead of a zod schema.
- A `Dialog` re-implemented as a fixed-position div with a manual backdrop and no focus trap.
- Icons from a different set (Heroicons, react-icons, Font Awesome) mixed in with lucide.
- Shadows stacked on top of borders (`shadow-lg border`) on a resting card.
- Interactive elements without a visible focus ring (`focus-visible:ring-*` removed).

## Examples

See `examples/shadcn/` — login, list and detail screens using the default neutral theme, the
semantic tokens and the standard component set:

- `examples/shadcn/login.png`
- `examples/shadcn/list.png`
- `examples/shadcn/detail.png`

Visual references for density, hierarchy and component choice. Write the real screens from the
components in `components/ui/`.
