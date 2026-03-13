# Phase 2.25: High-Fidelity Design (SuperDesign MCP)

## 🎯 Phase Objective
Generate polished, high-fidelity HTML screens from `styled-dsl.yaml` for visual approval before any code is written. This prevents expensive rework by catching design issues early.

## 📋 Required Tools
- `superdesign_generate` - Generate hi-fi HTML screens from DSL specifications
- `superdesign_iterate` - Refine screens based on user feedback
- `superdesign_gallery` - Create browsable gallery of all generated screens
- `dsl-generator` agent - Sync approved design changes back to `styled-dsl.yaml`

## 📚 Prerequisites
- Phase 2 outputs: `design-artifacts/styled-dsl.yaml`, `design-artifacts/theme.yaml`
- `design-artifacts/wireframes/` for layout reference
- User approval from Phase 2

## 🔧 Pre-flight Check
Before starting, verify SuperDesign MCP tools are available:

```bash
# Test tool availability by checking for superdesign_generate
# If tools are NOT available, provide setup instructions:
#   Add to MCP settings: npx -y github:AZidan/superdesign-mcp-claude-code
# Or offer to skip directly to Phase 2.5
```

If SuperDesign MCP is unavailable:
1. Inform the user that hi-fi screen generation requires the SuperDesign MCP server
2. Provide setup instructions: add `npx -y github:AZidan/superdesign-mcp-claude-code` to MCP config
3. Offer to skip Phase 2.25 and proceed directly to Phase 2.5 (API Architecture)

## 🚀 Execution Steps

### Step 2.25A: Generate Hi-Fi Screens
For each screen defined in `styled-dsl.yaml`:

```bash
# Read theme context
theme_context: design-artifacts/theme.yaml

# For each screen in styled-dsl.yaml:
superdesign_generate:
  design_type: "ui"
  framework: "html"
  prompt: "[Screen name] - [screen description from DSL] using theme: [colors, typography, spacing from theme.yaml]"
  variations: 1  # Start with 1 variation per screen, increase if user wants options

# Save outputs to design-artifacts/hifi-screens/
```

**Key prompt construction:**
- Include screen name, layout structure, and component details from `styled-dsl.yaml`
- Include color palette, typography, and spacing tokens from `theme.yaml`
- Reference wireframe layout for structural accuracy
- Specify responsive behavior if defined in DSL

### Step 2.25B: Generate Gallery for Review
```bash
superdesign_gallery → browse all generated screens in browser
```

Present the gallery URL to the user for comprehensive review of all screens.

### Step 2.25C: Feedback & Iteration Loop
```bash
# User reviews screens and provides feedback
# For each screen needing changes:
superdesign_iterate:
  design_file: "design-artifacts/hifi-screens/[screen-name].html"
  feedback: "[user's specific feedback]"
  variations: 1

# Regenerate gallery after iterations
superdesign_gallery
```

Repeat until user approves all screens.

### Step 2.25D: Sync Changes Back to DSL
If hi-fi design iterations introduced visual changes that differ from the original DSL:

```bash
dsl-generator: design-artifacts/hifi-screens/ → update design-artifacts/styled-dsl.yaml
  - Update color values, spacing, or typography if changed during hi-fi iteration
  - Add any new components or layout adjustments discovered during visual review
  - Maintain DSL structure and format consistency
```

Only run this step if design changes were made during iteration. Skip if screens were approved as-is.

## 📤 Expected Outputs
- `design-artifacts/hifi-screens/*.html` - High-fidelity HTML screens for all app screens
- `design-artifacts/styled-dsl.yaml` - Updated DSL (only if design changes were made)
- Visual gallery accessible in browser for stakeholder review

## ✅ Completion Criteria
- [ ] Hi-fi screens generated for ALL screens in `styled-dsl.yaml`
- [ ] Gallery generated and presented to user
- [ ] User has reviewed all screens in browser
- [ ] All feedback incorporated via iteration cycles
- [ ] `styled-dsl.yaml` synced with any design changes (if applicable)
- [ ] User explicitly approves all hi-fi screens

## 🚨 Critical Requirements
- **VISUAL FIDELITY**: Screens must accurately reflect `styled-dsl.yaml` structure and `theme.yaml` styling
- **THEME CONSISTENCY**: All screens must use the same design tokens from `theme.yaml`
- **USER APPROVAL MANDATORY**: Present gallery to user and wait for explicit approval of ALL screens
- **NO PROCEEDING**: Do not move to Phase 2.5 without approval
- **DSL SYNC**: Any approved design changes MUST be reflected back in `styled-dsl.yaml`
- **MCP DEPENDENCY**: If SuperDesign MCP is unavailable, offer skip option — do not block the pipeline

## ➡️ Phase Transition
Upon completion and approval:
1. Update `.archflow/current-phase.yaml` to `phase: 2.5`
2. Proceed to API Architecture Phase
3. Load `.archflow/phases/phase-2.5-api-architecture.md` for next phase instructions

---
**Phase 2.25 Complete** ✅ → **Phase 2.5: API Architecture** ➡️
