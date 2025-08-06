# Claude Code Subagents for Web + Native App Development (Optimized)
This document outlines a streamlined suite of 13 Claude Code subagents designed for token-efficient end-to-end development of cross-platform products. Each agent handles multiple related responsibilities within fixed technology stacks.

## 📋 Context Management System

**Create these reference files in your project (STRICT NAMING):**
- `project-context.md` - Business goals, tech stack, architecture decisions
- `roadmap.yaml` - Feature roadmap and sprint planning
- `current-feature.yaml` - Active development scope and requirements  
- `design-artifacts/user-flows.md` - User journey and flow documentation
- `design-artifacts/theme.yaml` - Design system and branding tokens
- `design-artifacts/wireframes/` - Screen wireframes and mockups
- `design-artifacts/styled-dsl.yaml` - Component specifications with styling
- `docs/api-contract.md` - API specifications for frontend/backend integration
- `src/components/[FeatureName]/` - Frontend component implementations
- `backend/src/[feature-name]/` - Backend service implementations
- `tests/[feature-name]/` - Test suites for each feature
- `tests/reports/` - QA and performance reports
- `docs/code-review-report.md` - Code quality assessment
- `.github/workflows/` - CI/CD pipeline configurations
- `deployment/` - Deployment and infrastructure configs

**Context Reference Syntax:**
```
agent-name: ref:project-context.md, current-feature.yaml → task description
```

## 🎯 Core Agents (13 Total)

### **Phase 1: Strategy & Planning**
- **`product-strategist`** - Business strategy, user personas, KPIs, market positioning
- **`feature-planner`** - Feature roadmaps, user stories, epic breakdown, sprint planning

### **Phase 2: Design**  
- **`ux-designer`** - User flows + visual design + themes + wireframes (merged ux-flow + theme)
- **`dsl-generator`** - Screen DSL creation + styling + component specs (merged screen-dsl + styled-dsl)

### **Phase 2.5: API Architecture**
- **`api-contract-architect`** - Creates API contracts from wireframes/requirements → docs/api-contract.md

### **Phase 3: Implementation**
- **`ui-engineer`** - All frontend (React, React Native, SwiftUI, Jetpack Compose, HTML/CSS)
- **`api-engineer`** - Backend services (NestJS, MySQL, REST APIs, authentication)
- **`qa-engineer`** - All testing (unit, integration, e2e, mobile, web) (merged ts-qa + native-qa)

### **Phase 4: Quality & Optimization**
- **`code-reviewer`** - Code quality, security, best practices across all platforms
- **`performance-optimizer`** - Performance analysis and optimization (web, mobile, backend)

### **Phase 5: Launch & Operations**
- **`devops-engineer`** - CI/CD, deployment, infrastructure, app store preparation (merged + release-manager)
- **`post-launch-analyst`** - Analytics, user insights, performance monitoring

### **Phase 6: Enhancement (On-Demand)**
- **`i18n-engineer`** - All localization (web, iOS, Android) (merged i18n + native-i18n)

## 🔁 Optimized Workflow

### **Token-Efficient Prompting**
```bash
# Abbreviated Syntax (saves ~50% tokens)
"product-strategist: fintech app strategy (B2B, SMB target)"
"ux-designer: onboarding flow + dark theme"
"dsl-generator: login.wireframe → styled-dsl.yaml"
"api-contract-architect: ref:wireframe → docs/api-contract.md"
# PARALLEL DEVELOPMENT:
"ui-engineer: login.dsl + api-contract → React + RN components (with API service layer)"
"api-engineer: ref:api-contract.md → user auth backend (JWT, bcrypt, email verify)"
# INTEGRATION:
"ui-engineer: connect frontend ↔ backend using api-contract"
"qa-engineer: test integrated auth feature (unit + integration + e2e)"
```

### **Phase-Based Execution (STRICT APPROVAL GATES)**
```yaml
Phase 1: Planning
  - product-strategist + feature-planner (parallel) 
  - Output: project-context.md, roadmap.yaml
  - ⚠️  MANDATORY USER APPROVAL GATE ⚠️

Phase 2: Design  
  - ux-designer: flows + themes → design-artifacts/
  - dsl-generator: wireframes → design-artifacts/styled-dsl.yaml
  - ⚠️  MANDATORY USER APPROVAL GATE ⚠️

Phase 2.5: API Architecture
  - api-contract-architect: wireframes + requirements → docs/api-contract.md
  - ⚠️  MANDATORY USER APPROVAL GATE ⚠️

Phase 3: Implementation (ONE FEATURE AT A TIME - PARALLEL DEVELOPMENT)
  - For EACH SINGLE feature (NEVER batch):
    - PARALLEL: ui-engineer + api-engineer work simultaneously using api-contract.md
      - ui-engineer: DSL → src/components/[FeatureName]/ (using contract for API calls)
      - api-engineer: api-contract → backend/src/[feature-name]/ (following contract exactly)
    - INTEGRATION: ui-engineer: connect frontend ↔ backend
    - TESTING: qa-engineer: test integrated feature → tests/[feature-name]/
    - ⚠️  MANDATORY FEATURE DEMO + USER APPROVAL AFTER FINISHING FEATURE IMPLEMENTATION AND INTEGRATION ⚠️
    - REPEAT for next feature ONLY after approval

Phase 4: Quality (ALL FEATURES COMPLETE)
  - qa-engineer: comprehensive testing → test reports
  - code-reviewer: quality review → review reports  
  - performance-optimizer: optimize (if needed) → performance reports
  - ⚠️  MANDATORY USER APPROVAL GATE ⚠️

Phase 5: Launch
  - devops-engineer: CI/CD + deployment → deployment configs
  - ⚠️  MANDATORY USER APPROVAL GATE ⚠️
  - post-launch-analyst: analytics setup → monitoring configs
  - ⚠️  MANDATORY USER APPROVAL GATE ⚠️
```

### **Workflow Instructions**

#### **CRITICAL REQUIREMENTS:**
1. **MANDATORY USER APPROVAL**: Stop and wait for explicit user approval after EVERY phase and feature iteration
2. **STRICT OUTPUT NAMING**: All agents MUST produce files with exact naming conventions specified below
3. **SPECIALIZED AGENTS ONLY**: NEVER use general-purpose agents when specialized agents exist
4. **NO PHASE SKIPPING**: Complete every phase in sequence - no exceptions
5. **🚨 API CONTRACT COMPLIANCE**: api-engineer MUST strictly follow docs/api-contract.md - NO DEVIATIONS ALLOWED

#### **OPTIMIZATION INSTRUCTIONS:**
- **Phase Batching**: Complete entire phases before moving forward to the next phase
- **Context Chaining**: Pass artifacts between agents: `ui-engineer: ref:styled-dsl.yaml → implement`
- **Minimal Context**: Reference files instead of pasting content
- **Parallel Execution**: Run independent agents concurrently within phases
- **Incremental Features**: One feature at a time with user approval

#### **Execution Steps:**

**0. Setup (STRICT FOLDER STRUCTURE)**
```bash
# Initialize ALL required directories and files
mkdir -p design-artifacts/wireframes specs docs frontend backend tests/reports .github/workflows deployment
touch project-context.md roadmap.yaml current-feature.yaml
touch design-artifacts/user-flows.md design-artifacts/theme.yaml design-artifacts/styled-dsl.yaml
touch docs/api-contract.md docs/code-review-report.md
```

**1. Strategy Phase** *(Parallel)*
```bash
product-strategist: define goals + personas → project-context.md
feature-planner: create roadmap → roadmap.yaml
```
**→ STOP: Present outputs to user → Wait for explicit approval before Phase 2**

**2. Design Phase** *(Sequential)*
```bash
ux-designer: ref:project-context.md → design-artifacts/user-flows.md + design-artifacts/theme.yaml
dsl-generator: ref:design-artifacts/wireframes → design-artifacts/styled-dsl.yaml
```
**→ STOP: Present design artifacts to user → Wait for explicit approval before Phase 2.5**

**2.5. API Architecture Phase** *(Sequential)*
```bash
api-contract-architect: ref:design-artifacts/wireframes + current-feature.yaml → docs/api-contract.md
```
**→ STOP: Present API contracts to user → Wait for explicit approval before Phase 3**

**3. Implementation Phase** *(Per Feature - PARALLEL DEVELOPMENT)*
```bash
# For EACH SINGLE feature in roadmap (ONE AT A TIME):

# STEP 3A: PARALLEL DEVELOPMENT (Run simultaneously)
ui-engineer: ref:design-artifacts/styled-dsl.yaml + docs/api-contract.md → src/components/[FeatureName]/
  - Build frontend components using contract for API integration points
  - Create service layers that match contract endpoints exactly

🚨 api-engineer: MUST READ + FOLLOW docs/api-contract.md EXACTLY → backend/src/[feature-name]/
   - VERIFY: All endpoints match contract paths, methods, parameters
   - VERIFY: All response structures match contract schemas  
   - VERIFY: All error codes match contract specifications
   - NO DEVIATIONS from contract allowed

# STEP 3B: INTEGRATION (After both frontend + backend complete)
ui-engineer: ref:docs/api-contract.md → connect frontend ↔ backend
  - Test API calls against actual backend endpoints
  - Verify data flow and error handling

# STEP 3C: FEATURE TESTING
qa-engineer: test integrated feature → tests/[feature-name]/
```
**→ MANDATORY STOP: Demo working integrated feature to user → Wait for explicit approval → Next feature**
**→ REPEAT for each feature individually**

**4. Quality Phase** *(Parallel)*
```bash
qa-engineer: comprehensive testing → tests/reports/test-results.md
code-reviewer: quality review → docs/code-review-report.md
performance-optimizer: performance analysis → docs/performance-report.md (if needed)
```
**→ STOP: Present quality reports to user → Wait for explicit approval before Phase 5**

**5. Launch Phase** *(Sequential)*
```bash
devops-engineer: setup CI/CD + deployment → .github/workflows/ + deployment/
post-launch-analyst: setup analytics + monitoring → docs/analytics-setup.md
```
**→ STOP: Present deployment plan to user → Wait for explicit approval before launch**

**6. Enhancement Phase** *(On-Demand)*
```bash
i18n-engineer: localize [specific-components] → locales/[lang]/ + i18n-config/
```
**→ STOP: Present localization to user → Wait for explicit approval**

### **Context Management Rules**

1. **File References Over Content**: Use `ref:filename.yaml` instead of pasting content
2. **Incremental Context**: Pass only delta changes between agents  
3. **Artifact Reuse**: Store DSL, themes, configs in `design-artifacts/` for reuse
4. **Feature Scoping**: Use `current-feature.yaml` to limit agent context to active work

## 💡 Critical Rules
- **SPECIALIZED AGENTS ONLY**: Never use `general-purpose` agent - always use specific agents (ui-engineer, api-engineer, qa-engineer, etc.)
- **🚨 API CONTRACT IS SACRED**: api-engineer MUST follow docs/api-contract.md exactly - zero tolerance for deviations
- **CONTRACT VERIFICATION**: Before implementation, api-engineer must confirm understanding of every endpoint, parameter, and response format
- **⚡ PARALLEL DEVELOPMENT**: With solid API contract, ui-engineer and api-engineer work simultaneously for maximum efficiency
- **INTEGRATION AFTER BUILD**: Frontend and backend integrate only after both are feature-complete
- **MANDATORY FILE NAMING**: Follow exact output naming conventions - no exceptions
- **USER APPROVAL GATES**: Stop and wait for explicit user approval after every phase and feature
- **ONE FEATURE AT A TIME**: Never batch features - implement and approve individually  
- **NO PHASE SKIPPING**: Complete every phase in exact sequence
- **TOKEN EFFICIENCY**: Use abbreviated prompt syntax and file references
- **ARTIFACT STORAGE**: Store all outputs in designated folders (`design-artifacts/`, `docs/`, `tests/`)