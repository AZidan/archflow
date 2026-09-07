# Onboarding — audit and extraction

Loaded by `phase-onboarding.md` when the inline audit runs. Not needed before that.

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
  Record it and redirect the user to **`/archflow:migrate`** (which retires sprints and splits the
  files into the v2.0 layout). Do not overwrite.
- **v2.x** (`schema_version: "2.0"` or `"2.1"`) → validate the split-file shape against the schemas in
  `.archflow/schemas/`. Collect **all** violations before recording — do not stop at the first failure.

**Index (`roadmap.yaml`, `roadmap-schema.yaml`)**
- Required keys: `schema_version: "2.1"`, `project`, `project_type`, `mode`, `epics`, `releases`
- `project_type` ∈ `fullstack | frontend_only | backend_only | mobile`; `mode` ∈ `quick | full`
- `epics` are LABELS: each has `id` (`^E[0-9]+$`), `name`, `scope` (`backend|frontend|mobile|both|unknown`) — no inline stories
- `releases[]`: each has `id` (slug), `status` (`planning|ready|in_progress`), `file`. At most ONE `in_progress`
- No `phases:` or `sprints:` keys anywhere

**Backlog (`backlog.yaml`, `backlog-schema.yaml`)**
- `epics[] → stories[]` are stubs: `id` (`^S[0-9]+-[0-9]+[a-z]?$`), `title`, `priority`, `status: backlog`, `description`

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
- Store found path in `.archflow/project-settings.yaml` as `api_contract_path`

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
