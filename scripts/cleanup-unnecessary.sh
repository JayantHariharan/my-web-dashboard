#!/bin/bash
# Aggressive cleanup of unnecessary/untracked files before push
# Only removes untracked files (won't delete any tracked or staged content)

set -e

echo "🧹 Cleaning up unnecessary untracked files..."

# Patterns to remove (expanded list for aggressive cleanup)
PATTERNS=(
    # Python
    "__pycache__"
    "*.pyc"
    "*.pyo"
    "*.pyd"
    "*.egg-info"
    ".coverage"
    "htmlcov"
    ".tox"
    ".mypy_cache"
    ".pytest_cache"

    # Node.js
    "node_modules/.cache"
    ".pnp.js"
    ".pnp.loader.mjs"
    "coverage"
    ".nyc_output"

    # Logs
    "*.log"
    "*.logs"
    "npm-debug.log"
    "yarn-debug.log"
    "yarn-error.log"

    # Temp files
    "*.tmp"
    "*.temp"
    ".tmp"
    ".temp"
    "tmp"
    "temp"

    # OS/IDE
    ".vscode"
    ".idea"
    "*.project"
    "*.classpath"
    "*.settings"
    ".DS_Store"
    "Thumbs.db"
    "*.swp"
    "*.swo"
    "*~"

    # Build artifacts
    "dist"
    "build"
    "target"
    "out"
    "bin"
    "obj"

    # Virtual envs
    ".venv"
    "venv"
    "env"
    ".envrc"

    # Misc
    ".cache"
    ".sass-cache"
)

# Find and delete only untracked files/directories
FOUND=0
while IFS= read -r -d '' path; do
    # Skip if empty
    [ -z "$path" ] && continue

    # Check if path is untracked
    if git status --porcelain "$path" 2>/dev/null | grep -q '^??'; then
        echo "  Removing: $path"
        rm -rf "$path" 2>/dev/null || true
        FOUND=1
    fi
done < <(find . \( -name ".git" -prune \) -o \( \
    $(for p in "${PATTERNS[@]}"; do printf "-name '%s' -o " "$p"; done | sed 's/ -o $//') \
    \) -print0 2>/dev/null)

if [ $FOUND -eq 0 ]; then
    echo "  No unnecessary untracked files found."
fi

echo "✅ Cleanup complete."
