# Phase: Onboarding (Existing Codebase)

This phase is loaded by `/archflow onboard`. It contains project type detection, audit logic, extraction rules, agent prompt templates, structured output schemas, and gap analysis for onboarding existing codebases into the phase-based framework.

The onboarding wizard runs in three phases:
- **Phase A**: Interactive Collection (gather all user input upfront)
- **Phase B**: Autonomous Agent Dispatch (specialized agents run in parallel with deep context)
- **Phase C**: Synthesis & Presentation (reconcile results and present to user)

---

## Project Type Detection

Detect the project type by scanning for structural indicators. Store the result in `.archflow/current-phase.yaml` as `project_type`.

### Detection Rules

**fullstack**
- Indicators: `frontend/ + backend/`, `src/ + api/`, `package.json` with both React and Express/NestJS deps
- Applicable phases: 1, 2, 2.25, 2.5, 3, 4, 5, 6
- Agents: ui-engineer, api-engineer, qa-engineer, ux-designer, all others

**frontend_only**
- Indicators: `src/components/` without `backend/`, `next.config.*`, `vite.config.*`, only React/Vue/Angular deps
- Applicable phases: 1, 2, 2.25, 3, 4, 5, 6 (no 2.5 unless consuming external APIs)
- Agents: ui-engineer, qa-engineer, ux-designer
- Notes: api-engineer not used; skip backend audit checks

**backend_only**
- Indicators: No `src/components/`, no `frontend/`, only Express/NestJS/Fastify deps, Dockerfile without frontend build
- Applicable phases: 1, 2.5, 3, 4, 5, 6 (no 2, 2.25)
- Agents: api-engineer, qa-engineer
- Notes: Skip Phase 2 and 2.25 entirely; Phase 2.5 (API contract) is the primary design artifact

**mobile**
- Indicators: `ios/`, `android/`, `react-native` in deps, `flutter`, SwiftUI files, Jetpack Compose files
- Applicable phases: 1, 2, 2.25, 2.5, 3, 4, 5, 6
- Agents: ui-engineer, api-engineer, qa-engineer, ux-designer

### Impact on Workflow

The detected `project_type` controls:
- Which phases are applicable (skip N/A phases)
- Which agents are available (no ui-engineer for backend-only)
- Which audit checks run (don't flag missing design artifacts for backend-only)
- Which onboarding agents are dispatched (see Agent Filtering Table)
- Roadmap structure (backend features = endpoints/services, frontend = pages/components)

---

## Agent Filtering by Project Type

| Agent | fullstack | frontend_only | backend_only | mobile |
|-------|-----------|---------------|--------------|--------|
| Codebase Audit | Yes | Yes | Yes | Yes |
| Doc Deep-Dive | Yes | Yes | Yes | Yes |
| Design Extraction | Yes | Yes | **No** | Yes |
| Route/API Extraction | Yes | Yes (client-side) | Yes (server-side) | Yes (client-side) |
| product-strategist | Yes | Yes | Yes | Yes |
| ux-designer | Yes | Yes | **No** | Yes |
| api-contract-architect | Yes | Yes | Yes | Yes |
| dsl-generator | Yes | Yes | **No** | Yes |
| feature-planner | Yes | Yes | Yes | Yes |

---

## Audit Checklist

Each check targets a specific phase artifact. Checks are filtered by `project_type`.

### Phase 1 Artifacts (Strategy)

**project_context** (weight: core)
- Scan for: `.archflow/project-context.md`, `README.md`, `docs/PRD.md`, `docs/requirements.md`
- Applicable to: all project types
- If found: mark Phase 1 as partial or complete
- If missing: flag for generation by product-strategist

**roadmap** (weight: core)
- Scan for: `.archflow/roadmap.yaml`, `roadmap.md`, `docs/roadmap.*`
- Applicable to: all project types
- If found at `.archflow/roadmap.yaml`: validate format against canonical schema (see **Roadmap Format Validation** below)
  - If valid: mark Phase 1 as complete, record `format_valid: true`
  - If violations found: mark Phase 1 as partial, record `format_valid: false` and collect all violations
- If found elsewhere (not `.archflow/roadmap.yaml`): mark Phase 1 as partial (needs migration to canonical path)
- If missing: flag for generation by feature-planner

### Roadmap Format Validation

When `.archflow/roadmap.yaml` is found, FIRST detect its schema version:

- **v1.0** (has a `phases:` key, or `schema_version` is absent or `"1.0"`) → do NOT validate v1 here.
  Record it and redirect the user to **`/archflow migrate`** (which retires sprints and splits the
  files into the v2.0 layout). Do not overwrite.
- **v2.0** (`schema_version: "2.0"`) → validate the split-file shape against the v2.0 schemas in
  `.archflow/schemas/`. Collect **all** violations before recording — do not stop at the first failure.

**Index (`roadmap.yaml`, `roadmap-schema.yaml`)**
- Required keys: `schema_version: "2.0"`, `project`, `project_type`, `mode`, `epics`, `releases`
- `project_type` ∈ `fullstack | frontend_only | backend_only | mobile`; `mode` ∈ `quick | full`
- `epics` are LABELS: each has `id` (`^E[0-9]+$`), `name`, `scope` (`backend|frontend|mobile|both|unknown`) — no inline stories
- `releases[]`: each has `id` (slug), `status` (`planning|ready|in_progress`), `file`. At most ONE `in_progress`
- No `phases:` or `sprints:` keys anywhere

**Backlog (`backlog.yaml`, `backlog-schema.yaml`)**
- `epics[] → stories[]` are stubs: `id` (`^S[0-9]+-[0-9]+$`), `title`, `priority`, `status: backlog`, `description`

**Releases (`releases/*.yaml`, `release-schema.yaml`)**
- Each: `id`, `name`, `goal`, `status` (`planning|ready|in_progress|released`), `stories[]`
- Each story: `id`, `title`, `priority`, readiness `status`, `gates {needs_design, needs_contract}`, `assigned`, `description`, `acceptance_criteria` (`{text, met}` objects), `subtasks` (`{text, completed}` objects)

**Referential integrity**
- Every `releases[]` ref points at an existing file; a story lives in exactly one place (backlog OR one release), never duplicated

**Recording violations**

Each violation entry:
```yaml
- path: "epics[0].stories[2].acceptance_criteria[1]"  # YAML path to the offending item
  rule: "acceptance_criteria item must be {text, met} object"
  found: "plain string: 'User can log in'"
```

---

### Phase 2 Artifacts (Design)

**design_system** (weight: nice-to-have)
- Scan for: `design-artifacts/theme.yaml`, `design-artifacts/styled-dsl.yaml`, `tailwind.config.*`
- Applicable to: fullstack, frontend_only, mobile
- Skip for: backend_only

### Phase 2.5 Artifacts (API Architecture)

**api_contract** (weight: core)
- Scan for: `docs/api-contract.md`, `swagger.json`, `swagger.yaml`, `openapi.json`, `openapi.yaml`, `docs/openapi.*`, `docs/swagger.*`
- Applicable to: fullstack, backend_only, mobile
- **use_existing: true** — if found in any format, USE AS-IS (do not convert)
- Store found path in `.archflow/current-phase.yaml` as `api_contract_path`

### Phase 3 Indicators (Implementation)

**frontend_code** (weight: indicator)
- Scan for: `src/`, `frontend/`, `app/`, `pages/`, `components/`
- Applicable to: fullstack, frontend_only, mobile

**backend_code** (weight: indicator)
- Scan for: `backend/`, `server/`, `api/`, `src/controllers/`, `src/routes/`
- Applicable to: fullstack, backend_only

**test_coverage** (weight: indicator)
- Scan for: `tests/`, `__tests__/`, `*.test.*`, `*.spec.*`
- Applicable to: all project types

### Phase 5 Indicators (Launch)

**cicd** (weight: indicator)
- Scan for: `.github/workflows/`, `.gitlab-ci.yml`, `Jenkinsfile`, `Dockerfile`
- Applicable to: all project types

---

## Structured Audit Output Schema

The inline codebase audit (Phase B, Layer 1) MUST output `.onboard-audit-report.yaml` in this format:

```yaml
project_name: "MyApp"
project_type: "fullstack"
tech_stack:
  language: "TypeScript"
  frontend: "React"
  backend: "NestJS"
  database: "PostgreSQL"
  orm: "Prisma"
  test_framework: "Jest"
  cicd: "GitHub Actions"

metrics:
  total_source_files: 245
  total_test_files: 38
  total_components: 42
  total_routes: 18
  total_modules: 7
  test_coverage_estimate: "partial"  # none | partial | comprehensive

phase_status:
  phase_1:
    status: "PARTIAL"  # DONE | PARTIAL | MISSING | N/A
    artifacts:
      project_context: { found: false, path: null }
      roadmap:
        found: false
        path: null
        format_valid: null        # null = not checked | true = valid | false = violations found
        format_violations: []     # list of {path, rule, found} objects; empty if format_valid is true or null
  phase_2:
    status: "MISSING"
    artifacts:
      design_system: { found: false, path: null }
      wireframes: { found: false, path: null }
  phase_2_5:
    status: "MISSING"
    artifacts:
      api_contract: { found: false, path: null }
  phase_3:
    status: "PARTIAL"
    indicators:
      frontend_code: { found: true, paths: ["src/", "frontend/"] }
      backend_code: { found: true, paths: ["backend/"] }
      test_coverage: { found: true, paths: ["tests/"], count: 38 }
  phase_5:
    status: "MISSING"
    indicators:
      cicd: { found: true, paths: [".github/workflows/"] }

recommended_phase: 3
recommended_phase_name: "Implementation"

# Detailed file inventory for agent consumption
file_inventory:
  config_files: ["package.json", "tsconfig.json", "nest-cli.json"]
  route_files: ["backend/src/controllers/*.ts"]
  component_files: ["frontend/src/components/**/*.tsx"]
  style_files: ["frontend/src/styles/**/*.css", "tailwind.config.js"]
  test_files: ["tests/**/*.spec.ts"]
  schema_files: ["prisma/schema.prisma"]
```

---

## Extraction Rules

### Design Token Extraction

The Design Extraction agent scans for design tokens in this priority order:

1. **Tailwind config** (`tailwind.config.*`): Extract `theme.extend` colors, spacing, fonts, breakpoints
2. **CSS variables** (`:root` blocks in CSS/SCSS files): Extract `--color-*`, `--font-*`, `--spacing-*`
3. **Theme files** (`theme.ts`, `theme.js`, `colors.ts`, `tokens.*`): Extract exported color/spacing/font objects
4. **Component patterns**: Scan components for repeated color values, font sizes, spacing values
5. **Styled-components themes**: Extract `ThemeProvider` values

Output format for `design-artifacts/theme.yaml`:
```yaml
colors:
  primary: "#3B82F6"
  secondary: "#10B981"
  # ...extracted values
typography:
  font_family: "Inter, sans-serif"
  sizes:
    sm: "0.875rem"
    base: "1rem"
    # ...
spacing:
  unit: "0.25rem"
  scale: [0, 1, 2, 4, 6, 8, 12, 16, 24, 32]
breakpoints:
  sm: "640px"
  md: "768px"
  lg: "1024px"
source: "tailwind.config.js"  # where tokens were primarily extracted from
```

Output format for `design-artifacts/extracted-components.yaml`:
```yaml
components:
  - name: "Button"
    path: "src/components/Button.tsx"
    variants: ["primary", "secondary", "outline"]
    props: ["size", "variant", "disabled", "onClick"]
  - name: "Card"
    path: "src/components/Card.tsx"
    variants: ["default", "elevated"]
    props: ["title", "children"]
patterns:
  naming_convention: "PascalCase"
  file_structure: "component-per-file"
  styling_approach: "tailwind"  # css-modules | styled-components | tailwind | inline
```

### Route/API Extraction

#### Server-Side Mode (fullstack, backend_only)

Scan for routes in framework-specific patterns:

- **NestJS**: `@Controller`, `@Get`, `@Post`, `@Put`, `@Delete`, `@Patch` decorators
- **Express**: `router.get()`, `router.post()`, `app.use()` patterns
- **Next.js API routes**: `pages/api/**` or `app/api/**/route.ts` file paths
- **Fastify**: `fastify.get()`, route schema definitions

For each route extract:
- HTTP method, path, path parameters
- Request body type (TypeScript interface if available)
- Response type (TypeScript interface if available)
- Auth middleware (e.g., `@UseGuards(AuthGuard)`, `authMiddleware`)
- Validation rules (class-validator decorators, Zod schemas, Joi)

#### Client-Side Mode (frontend_only, mobile)

Scan for API consumption patterns:

- **Fetch/Axios calls**: `fetch('/api/...')`, `axios.get('/api/...')`
- **React Query / TanStack Query**: `useQuery`, `useMutation` hooks with endpoint URLs
- **RTK Query**: `createApi` endpoint definitions
- **Custom service layers**: `apiService.get()`, `httpClient.post()` patterns
- **GraphQL**: `gql` tagged templates, `.graphql` files
- **SDK wrappers**: exported API functions with URL construction

For each discovered endpoint extract:
- HTTP method (inferred from function name or explicit)
- URL pattern (with path params)
- Request interface/type (TypeScript if available)
- Response interface/type (TypeScript if available)
- Auth token pattern (Bearer headers, cookie usage)
- Base URL configuration

Output format for `.onboard-extracted-routes.yaml`:
```yaml
extraction_mode: "server-side"  # or "client-side"
base_url: "/api/v1"
routes:
  - method: "GET"
    path: "/users"
    handler: "UsersController.findAll"
    file: "backend/src/controllers/users.controller.ts"
    line: 24
    auth: "JWT"
    response_type: "User[]"
  - method: "POST"
    path: "/users"
    handler: "UsersController.create"
    file: "backend/src/controllers/users.controller.ts"
    line: 35
    auth: "JWT"
    request_type: "CreateUserDto"
    response_type: "User"
    validation: ["class-validator"]
auth_patterns:
  type: "JWT"
  middleware: "AuthGuard"
  token_location: "Bearer header"
total_routes: 18
```

---

## Phase Status Determination

Based on audit results, determine each phase's status:

| Status | Meaning |
|--------|---------|
| DONE | All core artifacts exist and pass format validation |
| PARTIAL | Some artifacts exist, OR artifacts exist but have format violations |
| MISSING | No artifacts found |
| N/A | Not applicable for this project type |

> **Format validation rule**: a `roadmap.yaml` with `format_valid: false` counts as PARTIAL, not DONE, regardless of whether the file exists.

### Recommended Phase Logic

```
if all phases through 3 are DONE and tests exist:
  → recommend Phase 4 (Quality)
elif Phase 3 indicators exist (code written):
  → recommend Phase 3 (continue implementation)
elif Phase 2.5 is DONE (API contract exists):
  → recommend Phase 3 (start implementation)
elif Phase 2 is DONE:
  → recommend Phase 2.5 (API architecture)
elif Phase 1 is DONE:
  → recommend Phase 2 (Design) — or 2.5 for backend_only
else:
  → recommend Phase 1 (but backfill what we can)
```

---

## Agent Prompt Templates (Phase B)

### Doc Deep-Dive Agent

**Dispatch via:** Task tool with `subagent_type: "general-purpose"`

**Prompt template:**
```
You are performing a deep documentation dive for an existing project onboarding.

USER-PROVIDED LINKS:
{import_links}

ADDITIONAL DOCUMENTATION LINKS:
{additional_doc_links}

IMPORT SOURCE: {import_source}

INSTRUCTIONS:
1. For each user-provided link, fetch the content via the appropriate MCP tool or WebFetch.
2. For Jira items: fetch the item AND all children/subtasks. Follow every linked Confluence page.
3. For Confluence pages: follow internal links up to 2 levels deep (page → linked page → linked page).
4. For Notion pages: expand all toggle blocks and follow sub-pages.
5. For all other links: fetch the page content.

EXTRACT FROM EACH DOCUMENT:
- Title and type (epic, story, PRD, architecture doc, wiki page)
- Full description and body content
- Acceptance criteria (if present)
- Status and priority (if present)
- Architecture decisions and technical constraints
- Referenced technologies, libraries, or patterns
- Linked documents (follow them)

OUTPUT: Write a comprehensive organized document to `.onboard-imported-context.md` with all extracted content.
Organize by source, then by type (epics → stories → documentation → architecture decisions).
Include the source URL for each item.

Do NOT summarize — preserve full detail. This will be consumed by other agents.
```

### Design Extraction Agent

**Dispatch via:** Task tool with `subagent_type: "Explore"`

**Prompt template:**
```
You are extracting the design system from an existing codebase for onboarding.

PROJECT TYPE: {project_type}
TECH STACK: {tech_stack}

SCAN FOR DESIGN TOKENS (in priority order):
1. Tailwind config (tailwind.config.*): Extract theme.extend colors, spacing, fonts, breakpoints
2. CSS variables (:root blocks): Extract --color-*, --font-*, --spacing-* custom properties
3. Theme files (theme.ts, theme.js, colors.ts, tokens.*): Extract exported objects
4. Component patterns: Scan for repeated color values, font sizes, spacing
5. Styled-components themes: Extract ThemeProvider values

SCAN FOR COMPONENT INVENTORY:
- List all components with their file paths
- Identify variants, props, and patterns
- Determine naming conventions and file structure
- Identify styling approach (tailwind, CSS modules, styled-components, etc.)

OUTPUT TWO FILES:
1. `design-artifacts/theme.yaml` — Raw design tokens (colors, typography, spacing, breakpoints)
2. `design-artifacts/extracted-components.yaml` — Component inventory with props, variants, patterns

Use the structured formats defined in the project's onboarding phase documentation.
If no design tokens are found, output minimal files noting "no tokens extracted".
```

### Route/API Extraction Agent

**Dispatch via:** Task tool with `subagent_type: "Explore"`

**Prompt template (server-side):**
```
You are extracting API routes from a server-side codebase for onboarding.

PROJECT TYPE: {project_type}
TECH STACK: {tech_stack}

SCAN FOR ROUTES in framework-specific patterns:
- NestJS: @Controller, @Get, @Post, @Put, @Delete, @Patch decorators
- Express: router.get(), router.post(), app.use() patterns
- Next.js API routes: pages/api/** or app/api/**/route.ts file paths
- Fastify: fastify.get(), route schema definitions

FOR EACH ROUTE EXTRACT:
- HTTP method, path, path parameters
- Request body type (TypeScript interface if available)
- Response type (TypeScript interface if available)
- Auth middleware (e.g., @UseGuards(AuthGuard), authMiddleware)
- Validation rules (class-validator decorators, Zod schemas, Joi)
- File path and line number

OUTPUT: Write `.onboard-extracted-routes.yaml` using the structured format from the onboarding docs.
Include extraction_mode, base_url, routes list, auth_patterns, and total count.
```

**Prompt template (client-side):**
```
You are extracting API consumption patterns from a client-side codebase for onboarding.

PROJECT TYPE: {project_type}
TECH STACK: {tech_stack}

SCAN FOR API CONSUMPTION:
- Fetch/Axios calls: fetch('/api/...'), axios.get('/api/...')
- React Query / TanStack Query: useQuery, useMutation hooks with endpoint URLs
- RTK Query: createApi endpoint definitions
- Custom service layers: apiService.get(), httpClient.post() patterns
- GraphQL: gql tagged templates, .graphql files
- SDK wrappers: exported API functions with URL construction

FOR EACH ENDPOINT EXTRACT:
- HTTP method (inferred from function name or explicit)
- URL pattern (with path params)
- Request interface/type (TypeScript if available)
- Response interface/type (TypeScript if available)
- Auth token pattern (Bearer headers, cookie usage)
- Base URL configuration

OUTPUT: Write `.onboard-extracted-routes.yaml` using the structured format from the onboarding docs.
Set extraction_mode to "client-side". Include discovered base URLs and auth patterns.
```

### product-strategist (Onboarding Mode)

**Dispatch via:** Task tool with `subagent_type: "product-strategist"`

**Prompt template:**
```
You are reverse-engineering the product strategy from an existing codebase. This is NOT a greenfield project.

MODE: Reverse-engineer strategy from existing code + imported docs. Do NOT "define from scratch."

INPUTS:
- Imported context: Read `.onboard-imported-context.md` (fetched from {import_source})
- Audit report: Read `.onboard-audit-report.yaml`
- User vision notes: {user_vision_notes}
- Project type: {project_type}
- Tech stack: {tech_stack}

TASKS:
1. Synthesize a comprehensive `project-context.md` that documents:
   - What the product does (inferred from code + docs)
   - Target users and personas (from docs or inferred)
   - Tech stack and architecture decisions
   - Business goals and KPIs (from docs or inferred)
   - Key constraints and dependencies
2. Draft a roadmap skeleton as `.onboard-roadmap-draft.yaml` with features categorized:
   - completed: Features clearly built and working
   - in_progress: Features partially implemented
   - planned: Features documented but not started
   - proposed: User's vision notes and your strategic recommendations
3. For EVERY epic/feature, tag a `scope` field:
   - `backend`: Only requires backend work (API endpoints, services, database, cron jobs)
   - `frontend`: Only requires frontend work (UI components, pages, screens)
   - `mobile`: Only requires mobile app work (React Native, SwiftUI, Compose)
   - `both`: Requires both backend AND frontend/mobile work
   - `unknown`: Cannot determine scope from available information
   Determine scope by analyzing: which codebase areas the feature touches, whether it has UI components or API endpoints, and what the Jira epic/story describes. Even for cross-project epics (e.g., a mobile app epic imported into a backend repo), tag with the TRUE scope of the work — not the repo's project_type.
3. MUST use web search for domain research and competitive analysis (same depth as greenfield Phase 1)
4. MUST follow ALL linked content in the imported context — it's already fetched by the doc-dive agent

OUTPUT:
- Write `.archflow/project-context.md`
- Write `.onboard-roadmap-draft.yaml`

IMPORTANT: The roadmap draft uses status categories. The feature-planner will later convert this into proper roadmap.yaml format.
```

### ux-designer (Onboarding Mode)

**Dispatch via:** Task tool with `subagent_type: "ux-designer"`

**Prompt template:**
```
You are documenting the existing design system and user flows for an onboarding project.

MODE: Refine extracted design system, document existing user flows, describe existing screens.
Do NOT invent new screens — document what EXISTS and mark gaps.

INPUTS:
- Extracted theme: Read `design-artifacts/theme.yaml`
- Component inventory: Read `design-artifacts/extracted-components.yaml`
- Project context: Read `.archflow/project-context.md`

TASKS:
1. Refine `design-artifacts/theme.yaml`:
   - Normalize token names to standard format
   - Fill in missing tokens with reasonable defaults based on existing values
   - Add semantic tokens (success, warning, error) if raw values exist but aren't named
2. Document existing user flows in `design-artifacts/user-flows.md`:
   - Map the primary user journeys from existing screens/routes
   - Identify entry points, decision points, and exit points
   - Mark gaps where flows are incomplete
3. Create wireframe descriptions in `design-artifacts/wireframes/`:
   - Describe existing screens as wireframe specs (layout, components, data shown)
   - These describe what EXISTS, not new designs

OUTPUT:
- `design-artifacts/theme.yaml` (refined)
- `design-artifacts/user-flows.md`
- `design-artifacts/wireframes/` (screen descriptions)
```

### api-contract-architect (Onboarding Mode)

**Dispatch via:** Task tool with `subagent_type: "api-contract-architect"`

**Prompt template:**
```
You are formalizing extracted API routes into a proper API contract for an existing project.

MODE: Document what EXISTS. Mark unknowns where typing is incomplete.

INPUTS:
- Extracted routes: Read `.onboard-extracted-routes.yaml`
- Project context: Read `.archflow/project-context.md`

TASKS:
1. Convert extracted routes into a proper API contract at `docs/api-contract.md`
2. For each route:
   - Document method, path, description
   - Document request/response schemas (from extracted types)
   - Mark `unknown` for any missing type information
   - Document auth requirements
   - Document validation rules
3. Group endpoints by resource/domain
4. Add overview section with base URL, auth strategy, error format

OUTPUT: Write `docs/api-contract.md`

IMPORTANT: This documents the EXISTING API. Do not add endpoints that don't exist in the extraction.
```

### dsl-generator (Onboarding Mode)

**Dispatch via:** Task tool with `subagent_type: "dsl-generator"`

**Prompt template:**
```
Standard dsl-generator process: Convert wireframes + theme into styled-dsl.yaml.

INPUTS:
- Wireframes: Read `design-artifacts/wireframes/` (existing screen descriptions from ux-designer)
- Theme: Read `design-artifacts/theme.yaml` (refined by ux-designer)

These wireframes describe EXISTING screens, not new designs.

OUTPUT: Write `design-artifacts/styled-dsl.yaml`
```

### feature-planner (Onboarding Mode)

**Dispatch via:** Task tool with `subagent_type: "feature-planner"`

**Prompt template:**
```
You are converting a roadmap draft into the canonical Archflow roadmap.yaml format for an existing project.

INPUTS:
- Roadmap draft: Read `.onboard-roadmap-draft.yaml`
- Audit report: Read `.onboard-audit-report.yaml`
- Canonical schemas: Read `.archflow/schemas/roadmap-schema.yaml`, `backlog-schema.yaml`, `release-schema.yaml`
- Project type: {project_type}

CANONICAL OUTPUT FORMAT (v2.0 — Mode A):
Produce the v2.0 multi-file layout. There are NO `phases:`/`sprints:`. Epics are labels in the index;
unbuilt scope is stubs in the backlog; already-shipped scope becomes a `released` release under
`releases/archive/` + the `shipped` ledger.

```yaml
# .archflow/roadmap.yaml (index)
schema_version: "2.0"
project: "{project_name}"
project_type: {project_type}
mode: {quick|full}                 # full for a substantial codebase / multiple contributors
epics:                             # LABELS only
  - {id: E1, name: "Epic Name", scope: backend}   # backend|frontend|mobile|both|unknown
active_release: null               # or the in_progress slug
releases: []                       # planning/ready/in_progress refs (usually empty at onboard)
shipped: []                        # ledger of already-shipped releases (from existing code)
```
```yaml
# .archflow/backlog.yaml (stubs for unbuilt scope)
epics:
  - id: E1
    stories:
      - id: S1-01
        title: "Short Title"
        priority: High             # Critical|High|Medium|Low
        status: backlog
        description: "One line."
```
```yaml
# .archflow/releases/archive/{slug}.yaml (already-shipped scope, if code exists)
id: {slug}
name: "{Milestone}"
goal: "{what it delivered}"
status: released
stories:
  - id: S1-01
    title: "Short Title"
    priority: High
    status: done
    gates: {needs_design: false, needs_contract: true}
    assigned: api-engineer
    description: >
      Detailed description.
    acceptance_criteria: [{text: "Testable criterion", met: true}]   # {text,met} objects, NEVER strings
    subtasks: [{text: "Task", completed: true}]                       # {text,completed} objects
```

TASKS:
1. Group features into epic LABELS with `E{N}` IDs (id/name/scope only — no inline stories in the index).
2. Create stories with `S{epic}-{seq}` IDs. Derive per-story `gates {needs_design, needs_contract}` from scope.
3. **Route by state:** already-built/shipped code → a `released` release in `releases/archive/` +
   `shipped` ledger + a `history.yaml` entry. Unbuilt/proposed scope → backlog STUBS. In-progress code →
   an `in_progress` release (set `active_release`). At most ONE `in_progress`.
4. EVERY epic MUST have a `scope` (preserve from the draft; infer if missing; tag the TRUE scope).
5. Set `mode`: full for a substantial codebase / multiple contributors, else quick.
6. acceptance_criteria MUST be {text, met} objects; subtasks MUST be {text, completed} objects.

OUTPUT: Write `.archflow/roadmap.yaml` (index) + `.archflow/backlog.yaml` (stubs) + any
`.archflow/releases/archive/{slug}.yaml` + `.archflow/history.yaml`. Never write `phases:`/`sprints:`.
```

---

## Execution Dependency Graph (Phase B)

```
Layer 1 (all parallel, no dependencies):
  ├── Codebase Audit (inline)        → .onboard-audit-report.yaml
  ├── Doc Deep-Dive (Task subagent)  → .onboard-imported-context.md
  ├── Design Extraction (Task)       → design-artifacts/theme.yaml + extracted-components.yaml
  └── Route/API Extraction (Task)    → .onboard-extracted-routes.yaml

Layer 2 (waits for Layer 1):
  ├── product-strategist (Task)      → project-context.md + .onboard-roadmap-draft.yaml
  │   Inputs: .onboard-imported-context.md + .onboard-audit-report.yaml + user_vision_notes
  │
  ├── ux-designer (Task)             → theme.yaml (refined) + user-flows.md + wireframes/
  │   Inputs: theme.yaml (extracted) + extracted-components.yaml + project-context.md
  │   Waits for: Design Extraction + product-strategist
  │
  └── api-contract-architect (Task)  → docs/api-contract.md
      Inputs: .onboard-extracted-routes.yaml + project-context.md
      Waits for: Route/API Extraction + product-strategist

Layer 3 (waits for Layer 2):
  ├── dsl-generator (Task)           → design-artifacts/styled-dsl.yaml
  │   Inputs: wireframes/ + theme.yaml (refined)
  │   Waits for: ux-designer
  │
  └── feature-planner (Task)         → roadmap.yaml
      Inputs: .onboard-roadmap-draft.yaml + .onboard-audit-report.yaml
      Waits for: product-strategist
```

Main agent during Phase B:
1. Check dependency graph
2. Dispatch next available agent(s) via Task tool (parallel where possible, `run_in_background: true`)
3. Wait for completion, update `.onboard-progress.yaml` with agent status
4. Repeat until all agents complete
5. Main agent NEVER reads full agent output files during Phase B — only updates status

---

## Progress File Schema

```yaml
wizard_phase: "B"  # A | B | C
completed_steps: ["A1", "A2", "A3", "A4", "A5"]
user_inputs:
  project_type: "fullstack"
  tech_stack:
    language: "TypeScript"
    frontend: "React"
    backend: "NestJS"
    database: "PostgreSQL"
  import_source: "jira"  # jira | notion | linear | github | google_drive | trello | slack | confluence | local | conversational | skip
  import_links:
    - { url: "https://...", type: "epic" }
  additional_doc_links: ["https://..."]
  extract_design_system: true
  generate_api_contract: true
  existing_api_spec: null
  user_vision_notes: "Planning real-time collaboration in Q3"
  completed_features_override: ["user-auth"]
agent_outputs:
  codebase_audit: { status: "completed", output: ".onboard-audit-report.yaml" }
  doc_deep_dive: { status: "completed", output: ".onboard-imported-context.md" }
  design_extraction: { status: "running", output: null }
  route_extraction: { status: "pending", output: null }
  product_strategist: { status: "pending", output: null }
  ux_designer: { status: "pending", output: null }
  api_contract_architect: { status: "pending", output: null }
  dsl_generator: { status: "pending", output: null }
  feature_planner: { status: "pending", output: null }
```

---

## Canonical Roadmap Structure (v2.0 — multi-file)

All project types use the SAME structure. Project-type differentiation is handled by the `scope` field
on epics (labels), not by structural differences. **Epics are labels — they do NOT contain stories.**
Stories live in `backlog.yaml` (stubs) or a release file (detailed); a story is in exactly ONE place.

Use the "CANONICAL OUTPUT FORMAT (v2.0 — Mode A)" template earlier in this file as the authoritative
shape, and the split schemas: `roadmap-schema.yaml` (index), `backlog-schema.yaml` (stubs),
`release-schema.yaml` (detailed releases/stories), `history-schema.yaml`.

```yaml
# .archflow/roadmap.yaml — INDEX only (no stories under epics)
schema_version: "2.0"
project: "{name}"
project_type: "{fullstack|frontend_only|backend_only|mobile}"
mode: "{quick|full}"
epics:                                    # LABELS only
  - {id: E1, name: "Epic Name", scope: backend}   # backend|frontend|mobile|both|unknown
active_release: null                      # or the in_progress slug
releases: []                              # planning/ready/in_progress refs
shipped: []                               # ledger of shipped releases

# .archflow/backlog.yaml — stubs (unscheduled scope)
# .archflow/releases/{slug}.yaml — detailed stories (readiness status + gates + ACs + subtasks)
# .archflow/releases/archive/{slug}.yaml — shipped releases
# .archflow/history.yaml — shipped-story intent layer

# There is NO phases:/sprints: block. Instead:
#   - roadmap.yaml holds the index (mode, epic LABELS, releases[] pipeline, shipped[] ledger)
#   - backlog.yaml holds unbuilt scope as stubs
#   - releases/archive/{slug}.yaml holds already-shipped scope (status: released)
# See the "CANONICAL OUTPUT FORMAT (v2.0 — Mode A)" section above for the full shape.
```

**Key rules:**
- **Scope field is required on ALL epics** regardless of project type. It represents the TRUE scope of the work, which may differ from the repo's project_type (e.g., a "mobile app" epic imported into a backend repo should have `scope: mobile`).
- **Stories live in exactly one place** — a backlog stub OR one release file. Epics are labels; they don't contain stories in the index.
- **Every release story has `gates {needs_design, needs_contract}`** derived from scope.
- **acceptance_criteria** MUST be `{text, met}` objects, NEVER plain strings.
- **subtasks** MUST be `{text, completed}` objects.
- **Readiness status** values: `backlog | spec_ready | design_ready | contract_ready | ready | in_progress | review | done`.

---

## Phase C: Synthesis Rules

### C1: Roadmap Reconciliation

Read `roadmap.yaml` (index) + `backlog.yaml` + any `releases/*.yaml` + `.onboard-audit-report.yaml` +
user overrides from `.onboard-progress.yaml`:
- If a story is a backlog stub but audit shows the code exists/shipped → move it into a `released`
  release under `releases/archive/` + the `shipped` ledger + add a `history.yaml` entry.
- In-progress code → put those stories in the `in_progress` release (set `active_release`).
- If the user explicitly overrode a status in `completed_features_override` → use the user's status.
- Everything unbuilt stays as backlog stubs. Set `mode` (full for substantial repos, else quick).
- If `format_valid: false` (v2.0 shape): auto-fix before writing:
  - Plain-string `acceptance_criteria` → `{text: "...", met: false}`
  - Plain-string `subtasks` → `{text: "...", completed: false}`
  - Story missing `gates` → derive `{needs_design, needs_contract}` from scope
  - Invalid readiness `status` → map to the nearest pipeline state
  - Missing `scope` on epics → infer or default to `unknown`
  - More than one `in_progress` release → ask which is truly being built; others' stories → backlog

### C2: Phase Determination

Use the Recommended Phase Logic (above) with enriched audit data from `.onboard-audit-report.yaml`.

### C3: Gap Report

Generate gap report based on real agent outputs. Format:

```
+--------------------------------------------------+
|           PROJECT ONBOARDING AUDIT               |
+--------------------------------------------------+
|                                                  |
|  Project Type: [type] ([tech details])           |
|  Files: [N] source files, [M] test files         |
|                                                  |
|  Phase 1 (Strategy):     [status]                |
|    [checkmark/x] [artifact] [found/generated]    |
|    [warning]    roadmap.yaml — [N] format         |
|                 violations (see below)           |
|                                                  |
|  Phase 2 (Design):       [status or N/A]         |
|    [checkmark/x] [artifact] [found/generated]    |
|                                                  |
|  Phase 2.5 (API):        [status]                |
|    [checkmark/x] [artifact] [found/generated]    |
|                                                  |
|  Phase 3 (Implementation): [status]              |
|    [checkmark/x] [indicator details]             |
|                                                  |
|  Recommended starting phase: Phase [N]           |
+--------------------------------------------------+
```

N/A phases for the project type should show as: `Phase 2 (Design): N/A (backend only)`

If `format_valid: false`, append a violations block after the audit box:

```
roadmap format violations ([N] total):
  ⚠ releases/checkout.yaml → stories[2].acceptance_criteria[1]
    rule: acceptance_criteria item must be {text, met} object
    found: plain string: "User can log in"
  ⚠ releases/checkout.yaml → stories[0]
    rule: story must have gates {needs_design, needs_contract}
    found: missing gates
  ⚠ roadmap.yaml → releases
    rule: at most one release may be in_progress
    found: 2 in_progress (checkout, q3-launch)

These violations will be fixed during roadmap reconciliation (Step C1).
(A v1.0 roadmap is not shown here — it is redirected to /archflow migrate.)
```

### C4: Presentation Format

```
ONBOARDING COMPLETE

Project: [Name] ([Type]: [Tech Stack])
Recommended Phase: [N] ([Phase Name])

Generated Artifacts:
  ✅ project-context.md (by product-strategist — domain research + [source] synthesis)
  ✅ roadmap.yaml ([N] epics, [M] stories: [X] done, [Y] in-progress, [Z] backlog)
  ✅ API contract: docs/api-contract.md (reverse-engineered from [N] routes)
  ✅ Design system: design-artifacts/theme.yaml ([N] tokens extracted)
  ✅ Component specs: design-artifacts/styled-dsl.yaml ([N] screens)
  ✅ User flows: design-artifacts/user-flows.md

Review each artifact? [Yes / Trust the agents]
```

If "Yes": present each artifact for approval/editing, one at a time.

### C5: Finalization

1. Create `.archflow/current-phase.yaml` with full schema (see onboard.md)
2. Create or update `CLAUDE.md` with Archflow section (see onboard.md for full template):
   - If `CLAUDE.md` does NOT exist: create it with project overview, common commands, architecture, and Archflow section — all derived from onboarding analysis
   - If `CLAUDE.md` ALREADY exists: append the Archflow section to the end
   - The Archflow section MUST include: current phase, links to project-context.md, roadmap.yaml, api-contract.md (if generated), and available `/archflow` commands
   - Only list artifacts that were actually created
3. Clean up ALL temporary `.onboard-*` files (`rm .onboard-*`). No `.onboard-*` files should remain after finalization
4. Offer to remove onboarding-only MCPs
5. Print summary with next steps (include CLAUDE.md in the created artifacts list)

---

## Error Handling

**Agent failure:** Record in `.onboard-progress.yaml`, continue with non-dependent agents, report failed artifacts in Phase C with manual fallback options (import/describe/skip).

**MCP unavailable:** WebFetch fallback for Confluence/documentation pages. If auth required, ask user to paste content manually. Product-strategist runs with reduced context.

**Design extraction fails:** ux-designer receives empty extraction, falls back to creating fresh theme from project-context.md.

**Resume after interruption:** `.onboard-progress.yaml` tracks `wizard_phase` (A/B/C) and per-agent status. On resume: Phase A re-asks from interrupted step, Phase B re-dispatches incomplete agents, Phase C re-runs synthesis.

---

## State Bridging (File-Based Handoff)

| From | Output File | Consumed By |
|------|-------------|-------------|
| Phase A (main) | `.onboard-progress.yaml` | All agents (user inputs) |
| Audit (inline) | `.onboard-audit-report.yaml` | product-strategist, feature-planner, Phase C |
| Doc Deep-Dive | `.onboard-imported-context.md` | product-strategist |
| Design Extraction | `design-artifacts/theme.yaml`, `extracted-components.yaml` | ux-designer |
| Route Extraction | `.onboard-extracted-routes.yaml` | api-contract-architect |
| product-strategist | `project-context.md`, `.onboard-roadmap-draft.yaml` | ux-designer, api-contract-architect, feature-planner |
| ux-designer | `theme.yaml` (refined), `wireframes/` | dsl-generator |
| api-contract-architect | `docs/api-contract.md` | Phase C |
| dsl-generator | `design-artifacts/styled-dsl.yaml` | Phase C |
| feature-planner | `roadmap.yaml` | Phase C (reconciliation) |

Temporary files (`.onboard-*`) cleaned up in Phase C Step C5.

---

**This file is loaded by the `/archflow onboard` skill. It provides extraction rules, schemas, agent templates, and synthesis logic; the skill provides the orchestration flow.**
