#!/bin/sh
# Archflow git pre-push guard — host-independent fallback for hooks/guard-git.mjs.
# Installed to .git/hooks/pre-push by `archflow-install-git-guard.sh` (or doctor --fix).
# Blocks: (1) a non-fast-forward (force) push to main/master; (2) any push to main/master
# while an Archflow autopilot run is live. Everything else passes. Fails open on error.
remote="$1"; url="$2"
zero=0000000000000000000000000000000000000000
live_run=""
for f in .archflow/autopilot/*.yaml; do
  [ -f "$f" ] || continue
  if grep -Eq '^\s*status:\s*(running|preflight)' "$f" 2>/dev/null; then live_run="$f"; break; fi
done
while read -r local_ref local_sha remote_ref remote_sha; do
  case "$remote_ref" in refs/heads/main|refs/heads/master) ;; *) continue ;; esac
  if [ -n "$live_run" ]; then
    echo "Blocked by Archflow: push to ${remote_ref#refs/heads/} during autopilot run ($live_run)." >&2
    echo "Autopilot never merges to main; finish the run and merge yourself." >&2
    exit 1
  fi
  if [ "$local_sha" = "$zero" ]; then
    echo "Blocked by Archflow: deleting ${remote_ref#refs/heads/} on $remote." >&2; exit 1
  fi
  if [ "$remote_sha" != "$zero" ] && ! git merge-base --is-ancestor "$remote_sha" "$local_sha" 2>/dev/null; then
    echo "Blocked by Archflow: force-push to ${remote_ref#refs/heads/} on $remote (remote is not an ancestor of local)." >&2
    echo "Archflow does not rewrite history on main in a project it manages. Run it yourself outside the agent if intended." >&2
    exit 1
  fi
done
exit 0
