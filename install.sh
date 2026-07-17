#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HERMES_HOME="${HERMES_HOME:-$HOME/.hermes}"
SKILLS_DIR="$HERMES_HOME/skills/software-development"

echo "task-framework-skills installer"
echo ""

mkdir -p "$SKILLS_DIR"

for skill in task-framework task-tracker task-timestamp-convention \
             task-lifecycle-edge-cases task-lifecycle-portability \
             task-external-repos-pattern; do
  src="$SCRIPT_DIR/skills/$skill"
  dst="$SKILLS_DIR/$skill"
  [ ! -d "$src" ] && { echo "  ✗ Source not found: $src"; continue; }

  if [ "${1:-}" = "--symlink" ]; then
    [ -e "$dst" ] && rm -rf "$dst"
    ln -sfn "$src" "$dst"
    echo "  → Symlinked: $skill"
  else
    rm -rf "$dst"
    cp -r "$src" "$dst"
    echo "  ✓ Installed: $skill"
  fi
done

echo ""
echo "Done. Add to config.yaml:"
echo "  skills.config.skill-graph.source_dirs:"
echo "    - $SKILLS_DIR"
