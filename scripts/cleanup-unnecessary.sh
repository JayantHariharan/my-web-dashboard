#!/bin/bash
# Aggressive cleanup of unnecessary/untracked files before push
# Only removes untracked files (won't delete any tracked or staged content)

set -e

# Default options
DRY_RUN=0
VERBOSE=0

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --dry-run|-n)
            DRY_RUN=1
            shift
            ;;
        --verbose|-v)
            VERBOSE=1
            shift
            ;;
        --help|-h)
            echo "Usage: $0 [OPTIONS]"
            echo "Clean up unnecessary untracked files before git push"
            echo ""
            echo "Options:"
            echo "  --dry-run, -n    Show what would be deleted without removing"
            echo "  --verbose, -v    Show detailed output including sizes"
            echo "  --help, -h       Show this help message"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

echo "🧹 Cleaning up unnecessary untracked files..."
if [ $DRY_RUN -eq 1 ]; then
    echo "   (DRY RUN mode - no files will be deleted)"
fi
echo ""

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
    ".pytype"

    # Node.js/Playwright
    "node_modules/.cache"
    ".pnp.js"
    ".pnp.loader.mjs"
    "coverage"
    ".nyc_output"
    "playwright-report"
    "test-results"
    ".cache"
    ".npm"

    # Logs
    "*.log"
    "*.logs"
    "npm-debug.log"
    "yarn-debug.log"
    "yarn-error.log"
    "lerna-debug.log"

    # Temp files
    "*.tmp"
    "*.temp"
    ".tmp"
    ".temp"
    "tmp"
    "temp"
    ".temp"

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
    ".directory"

    # Build artifacts
    "dist"
    "build"
    "target"
    "out"
    "bin"
    "obj"
    ".next"
    ".nuxt"

    # Virtual envs
    ".venv"
    "venv"
    "env"
    ".envrc"
    ".python-version"

    # Package/dependency caches
    ".npm"
    ".yarn"
    ".pnpm-store"
    "package-lock.json"  # Only if untracked (not in git)
    "yarn.lock"          # Only if untracked

    # Misc
    ".cache"
    ".sass-cache"
    ".gradle"
)

# Counters
TOTAL_FILES=0
TOTAL_SIZE=0

# Build find expression parts
EXPRESSION=()
for p in "${PATTERNS[@]}"; do
    EXPRESSION+=(-name "$p" -o)
done

# Remove trailing -o
if [ ${#EXPRESSION[@]} -gt 0 ]; then
    unset 'EXPRESSION[${#EXPRESSION[@]}-1]'
fi

# Find and delete only untracked files/directories
if [ $VERBOSE -eq 1 ]; then
    echo "Scanning for untracked files matching patterns..."
fi

# Use git ls-files to get all tracked files, then find untracked ones
# This is safer than checking each file individually
while IFS= read -r path; do
    # Skip if empty
    [ -z "$path" ] && continue

    # Check if path is untracked (safety check)
    if git status --porcelain "$path" 2>/dev/null | grep -q '^??'; then
        if [ -e "$path" ]; then
            # Get size if file
            SIZE=0
            if [ -f "$path" ]; then
                SIZE=$(stat -c%s "$path" 2>/dev/null || stat -f%z "$path" 2>/dev/null || echo 0)
            fi

            TOTAL_FILES=$((TOTAL_FILES + 1))
            TOTAL_SIZE=$((TOTAL_SIZE + SIZE))

            if [ $DRY_RUN -eq 1 ]; then
                if [ $VERBOSE -eq 1 ]; then
                    echo "  [DRY RUN] Would remove: $path ($(numfmt --to=iec-i --suffix=B $SIZE 2>/dev/null || echo "${SIZE}B")"
                else
                    echo "  [DRY RUN] Would remove: $path"
                fi
            else
                if [ $VERBOSE -eq 1 ]; then
                    echo "  Removing: $path ($(numfmt --to=iec-i --suffix=B $SIZE 2>/dev/null || echo "${SIZE}B")"
                else
                    echo "  Removing: $path"
                fi
                rm -rf "$path" 2>/dev/null || true
            fi
        fi
    fi
done < <(find . -type f -o -type d "${EXPRESSION[@]}" 2>/dev/null | grep -v '^\./\.git')

if [ $TOTAL_FILES -eq 0 ]; then
    echo "  ✅ No unnecessary untracked files found."
else
    if [ $DRY_RUN -eq 1 ]; then
        echo ""
        echo "📊 Dry run summary:"
        echo "   Files that would be removed: $TOTAL_FILES"
        echo "   Total space that would be freed: $(numfmt --to=iec-i --suffix=B $TOTAL_SIZE 2>/dev/null || echo "${TOTAL_SIZE}B")"
    else
        echo ""
        echo "✅ Cleanup complete: removed $TOTAL_FILES files, freed $(numfmt --to=iec-i --suffix=B $TOTAL_SIZE 2>/dev/null || echo "${TOTAL_SIZE}B")"
    fi
fi

