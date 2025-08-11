# Phase Setup & Inference System

This file is loaded ONLY when `current-phase.yaml` is missing from a project directory. It handles phase detection and initialization.

## 🔍 Smart Phase Detection Logic

### Detection Flow
```bash
if [[ -f "current-phase.yaml" ]]; then
  # Normal operation - use existing tracker
  Current Phase: ref:current-phase.yaml → phase_file
elif [[ -f "current-feature.yaml" ]]; then
  # Existing project without phase tracker - infer phase
  Infer Phase: ref:current-feature.yaml → determine current phase
  Create: current-phase.yaml based on inference
else
  # New project - start from Phase 1
  cp ~/.claude/current-phase.yaml ./current-phase.yaml
fi
```

## 🎯 Phase Inference Rules

### Keyword-Based Detection
Analyze `current-feature.yaml` content for these keywords:

**Phase 1 (Strategy & Planning):**
- Keywords: "business goals", "personas", "planning", "strategy", "market", "target users"
- Indicators: Project defining scope and objectives

**Phase 2 (Design):**
- Keywords: "wireframes", "user flows", "design", "mockups", "themes", "ui/ux", "prototypes"
- Indicators: Design artifacts being created

**Phase 2.5 (API Architecture):**
- Keywords: "api contract", "endpoints", "schemas", "api spec", "swagger", "openapi"
- Indicators: API contracts being defined

**Phase 3 (Implementation):**
- Keywords: "components", "backend", "frontend", "implementation", "development", "coding"
- Indicators: Active development work

**Phase 4 (Quality):**
- Keywords: "testing", "code review", "performance", "quality", "qa", "optimization"
- Indicators: Quality assurance activities

**Phase 5 (Launch):**
- Keywords: "deployment", "ci/cd", "monitoring", "launch", "production", "release"
- Indicators: Deployment and operations setup

**Phase 6 (Enhancement):**
- Keywords: "localization", "optimization", "enhancement", "i18n", "improvements"
- Indicators: Post-launch improvements

## 🔄 Inference Process

### Step-by-Step Detection
1. **Read** `current-feature.yaml` content
2. **Count** keyword matches for each phase
3. **Select** phase with highest keyword count
4. **Create** `current-phase.yaml` with detected phase
5. **Load** appropriate phase instruction file

### Example Inference
```yaml
# current-feature.yaml content analysis:
Content: "Working on user registration wireframes and login flow design"
Keywords Found:
  - Phase 2: "wireframes", "design" (2 matches)
  - Phase 3: "user registration", "login" (1 match)
Result: Phase 2 (Design) - highest match count
```

## ⚠️ Fallback Logic

### Manual Override
If automatic inference fails:
```bash
# Prompt user for manual phase selection
echo "Could not automatically detect project phase."
echo "Please specify current development phase (1-6):"
echo "1. Strategy & Planning"
echo "2. Design"
echo "3. Implementation" 
echo "4. Quality"
echo "5. Launch"
echo "6. Enhancement"
```

### Default Behavior
- **No feature context**: Default to Phase 1
- **Ambiguous keywords**: Ask user to clarify
- **Multiple high scores**: Choose earliest phase (safer)

## 📋 Phase Template Creation

### Generated current-phase.yaml
```yaml
# Auto-generated from inference
phase: {detected_phase}
phase_name: "{detected_phase_name}"
phase_file: "phases/phase-{detected_phase}-{name}.md"

# Inference metadata
inferred_from: "current-feature.yaml"
inference_confidence: "high|medium|low"
inference_keywords: ["keyword1", "keyword2"]
created_by: "phase-setup-system"
created_at: "{timestamp}"

# Standard phase tracking
phases_completed: []
current_feature: null
feature_status: "detected"
status: "ready"
last_updated: null
completed_at: null
```

---
**This file is only loaded during project initialization when current-phase.yaml is missing.**