# Claude Code Subagents (Phase-Based System)
Dynamic phase-based instruction loading for token-efficient development.

## 🎯 Core Agents (Always Available)

**Phase 1: Strategy & Planning**
- `product-strategist` - Business strategy, personas, KPIs → project-context.md
- `feature-planner` - Feature roadmaps, user stories, sprint planning → roadmap.yaml

**Phase 2: Design**  
- `ux-designer` - User flows, design systems, themes, wireframes → design-artifacts/
- `dsl-generator` - Component specifications with styling → design-artifacts/styled-dsl.yaml

**Phase 2.5: API Architecture**
- `api-contract-architect` - API contracts from wireframes → docs/api-contract.md (single source of truth)

**Phase 3: Implementation**
- `ui-engineer` - All frontend (React, React Native, SwiftUI, Jetpack Compose) + integration
- `api-engineer` - NestJS/MySQL backends, MUST follow docs/api-contract.md exactly (zero tolerance)
- `qa-engineer` - Comprehensive testing (unit, integration, e2e) across all platforms

**Phase 4: Quality & Optimization**
- `code-reviewer` - Code quality, security, best practices analysis + improvement reports
- `performance-optimizer` - Performance bottleneck identification and optimization

**Phase 5: Launch & Operations**
- `devops-engineer` - CI/CD pipelines, deployment infrastructure, app store preparation
- `post-launch-analyst` - Analytics implementation, user insights, performance monitoring

**Phase 6: Enhancement (On-Demand)**
- `i18n-engineer` - Internationalization for web/iOS/Android platforms

## 🔄 Dynamic Phase Loading

**Current Phase Detection:**
```yaml
# Read current-phase.yaml to determine active phase
phase: 1  # Current phase number
phase_file: "phases/phase-1-strategy.md"  # Load this file for detailed instructions
```

**Phase Instruction Loading:**
```bash
# Check for existing phase tracker
if [[ -f "current-phase.yaml" ]]; then
  # Normal operation - use existing tracker
  Current Phase: ref:current-phase.yaml → phase_file
  Detailed Instructions: ref:phases/phase-{current}-{name}.md
else
  # Project setup needed - load setup system
  Setup Required: ref:phases/phase-setup.md → detect and initialize phase
fi
```

## 📋 Universal Context Files (Always Required)
- `project-context.md` - Business goals, tech stack, architecture decisions
- `roadmap.yaml` - Feature roadmap and sprint planning
- `current-feature.yaml` - Active development scope and requirements  
- `current-phase.yaml` - Phase state tracker (PROJECT-SCOPED, auto-created from template)

## 💡 Universal Critical Rules (Apply to ALL Phases)

### 🚨 API Contract Compliance (Phases 2.5-4)
- **API CONTRACT IS SACRED**: api-engineer MUST follow docs/api-contract.md exactly
- **ZERO TOLERANCE**: No deviations from contract specifications allowed
- **CONTRACT VERIFICATION**: Must confirm understanding before implementation

### ⚠️ Mandatory Approval Gates (ALL Phases)
- **USER APPROVAL REQUIRED**: Stop and wait for explicit user approval after EVERY phase
- **NO PHASE SKIPPING**: Complete every phase in exact sequence
- **DEMO REQUIRED**: Working features must be demonstrated before approval

### 🎯 Agent Selection Rules (ALL Phases)
- **SPECIALIZED AGENTS ONLY**: Always use sub-agents when possible. Never use `general-purpose` agent
- **PHASE-APPROPRIATE AGENTS**: Only use agents listed for current phase
- **MANDATORY FILE NAMING**: Follow exact output naming conventions

### 🗺️ Codemap Navigation (ALL Phases)
- **CODEMAP FIRST**: Always use `codemap find` before reading full files or using grep/glob
- **TARGETED READS**: Use `codemap show` to get file structure, then read only the relevant line ranges
- **INIT ON SETUP**: Run `codemap init .` when starting any new project, then `codemap watch . -q &`
- **VALIDATE BEFORE TRUSTING**: Run `codemap validate` before using cached line numbers after compaction
- **See `.claude/skills/codemap/SKILL.md`** for full usage guide

### ⚡ Development Efficiency (ALL Phases)
- **PARALLEL DEVELOPMENT**: Run compatible agents simultaneously when possible
- **TOKEN EFFICIENCY**: Use `ref:filename.yaml` instead of pasting content. Use `codemap find` + targeted line reads instead of full file scans
- **ONE FEATURE AT A TIME**: Never batch features in Phase 3

## 🔄 Phase Navigation System

### Phase Transition Workflow
```yaml
Current Phase Complete:
  1. Validate all completion criteria met
  2. Present outputs to user
  3. Wait for explicit user approval
  4. Update current-phase.yaml to next phase
  5. Load ref:phases/phase-{next}.md for next instructions

Phase Files Available:
  - phases/phase-1-strategy.md
  - phases/phase-2-design.md  
  - phases/phase-2.5-api-architecture.md
  - phases/phase-3-implementation.md
  - phases/phase-4-quality.md
  - phases/phase-5-launch.md
  - phases/phase-6-enhancement.md
```

### Project Setup (When Needed)
For projects without `current-phase.yaml`:
- **Load Setup System**: `ref:phases/phase-setup.md`
- **Phase Detection**: Automatic inference from project state
- **Initialization**: Create phase tracker and load instructions

## 🚀 Getting Started

**On Every New Session (ALWAYS do this first):**
```bash
# Start codemap watch if not already running
pgrep -f "codemap watch" > /dev/null || codemap watch . -q &
```

**Normal Operation (current-phase.yaml exists):**
1. Start codemap watch (above)
2. Load current phase from `current-phase.yaml`
3. Load detailed instructions from `ref:phases/phase-{current}.md`
4. Follow phase-specific execution steps
5. Complete approval gates before proceeding to next phase

**Project Setup (current-phase.yaml missing):**
1. Start codemap watch (above)
2. Load setup system from `ref:phases/phase-setup.md`
3. Auto-detect phase from project state or start Phase 1
4. Create `current-phase.yaml` and continue with normal operation

**File Structure:**
- `current-phase.yaml` - Project phase state (auto-created if missing)
- `phases/phase-setup.md` - Setup system (loaded only when needed)
- `phases/phase-*.md` - Phase-specific instructions (loaded based on current phase)

---
**📍 Current Phase Instructions: Load ref:{current-phase.yaml → phase_file}**