# /archflow mode — Show or switch the ceremony mode (quick | full)

`mode` is a profile over the SAME v2.0 schema, not a fork. It governs how much ceremony is enforced.
Switching is an in-place change — no data rewrite, because the schema is identical in both modes.

## Usage
```
/archflow mode          → show the current mode + what it means
/archflow mode full     → switch to full
/archflow mode quick    → switch to quick
```

## The two modes

| Concern | `quick` (small / solo) | `full` (team / scale) |
|---|---|---|
| Releases | one implicit release; no create/ship ceremony until asked | explicit release pipeline + ship ritual |
| Backlog | stories may live directly in the release | backlog stubs → promote → detailed |
| Readiness gates | **auto-satisfied** (exist but don't block) | enforced **advisory-recorded** (`started_ungated` on override) |
| Approval gates | proceed unless the user stops you | explicit per-phase approval |
| Roles | one lane (solo) | PM / designer / architect / engineer / QA lanes |

## Show current mode (no argument)
Read `mode` from `.archflow/roadmap.yaml` (source of truth; mirrored in `current-phase.yaml`). Print
it and a one-line description. If absent, treat as `quick` and offer to record it.

## Switch mode
1. Set `mode` in `.archflow/roadmap.yaml` AND `.archflow/current-phase.yaml`.
2. **quick → full** (materialize ceremony in place, no data loss):
   - If a single implicit release holds everything, keep it as the active release; ensure its file
     exists under `.archflow/releases/` and it's registered in `roadmap.yaml → releases`.
   - Ensure `backlog.yaml` exists (may be empty); future scope becomes stubs.
   - Turn readiness gates ON (advisory-recorded from here on).
3. **full → quick** (collapse ceremony):
   - Gates become advisory-off (auto-satisfied). Existing release files and history are left intact.
   - Use for a project that over-scoped itself; nothing is deleted.
4. Commit:
   ```bash
   git add .archflow/roadmap.yaml .archflow/current-phase.yaml
   git commit -m "chore: switch archflow mode to {quick|full}"
   ```

## Smart graduation prompt (offered by the framework, never forced)
When a `quick` project shows growth signals, OFFER (do not auto-switch) a move to `full`:
- the user asks for a **second release**, or
- a **second contributor** appears, or
- the project **crosses a size threshold** (story count / file count / repo age).

Prompt: "This project looks like it's outgrowing quick mode (<reason>). Switch to full mode? It adds
explicit releases and role-based design/spec gates. `/archflow mode full` — or keep going as is."
Remember a decline so it doesn't nag every session.
