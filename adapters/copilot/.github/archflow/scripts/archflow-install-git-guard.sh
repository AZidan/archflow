#!/bin/sh
# Installs the Archflow pre-push guard into this repo's .git/hooks (chains an existing hook).
set -e
root="$(git rev-parse --show-toplevel)"; hooks="$(git rev-parse --git-path hooks)"
src="$(cd "$(dirname "$0")" && pwd)/archflow-pre-push.sh"
mkdir -p "$hooks"
if [ -f "$hooks/pre-push" ] && ! grep -q archflow-pre-push "$hooks/pre-push"; then
  mv "$hooks/pre-push" "$hooks/pre-push.pre-archflow"
  printf '#!/bin/sh\n"%s" "$@" <&0 || exit 1\nexec "%s" "$@"\n' "$src" "$hooks/pre-push.pre-archflow" > "$hooks/pre-push"
else
  printf '#!/bin/sh\nexec "%s" "$@"\n' "$src" > "$hooks/pre-push"
fi
chmod +x "$hooks/pre-push" "$src"
echo "Archflow pre-push guard installed at $hooks/pre-push"
