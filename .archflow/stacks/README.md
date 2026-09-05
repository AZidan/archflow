# Stack profiles

A stack profile is a **starting point offered by `/archflow:init`**, never a fallback an agent
silently inherits.

The agents carry no technology of their own. They read `stack:` from `.archflow/current-phase.yaml`
and work in what it names. A `null` field means *not determined*: the agent says what it found,
names the candidates, and asks. It never assumes and never installs.

These files exist so that starting a project is one choice rather than eleven. Pick one at init,
adjust any field, or skip them entirely and answer field by field. Nothing reads them again
afterwards — once `stack:` is written to `current-phase.yaml`, that is the only source of truth.

## Adding a profile

One file per profile, named for what it is. Keep it to technologies that genuinely travel together;
a profile that needs a paragraph of caveats should be two profiles. Every field in
`current-phase-schema.yaml` under `stack:` is available, and omitting a field is better than
guessing it, because omission asks the user while a wrong value silently misdirects an agent.
