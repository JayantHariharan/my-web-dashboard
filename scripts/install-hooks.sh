#!/bin/bash
# Install git hooks into .git/hooks/

set -e

echo "🔧 Installing git hooks..."

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
HOOKS_DIR="$REPO_ROOT/.git/hooks"
TEMPLATES_DIR="$REPO_ROOT/scripts/templates"

# Ensure .git/hooks exists
mkdir -p "$HOOKS_DIR"

# List of hooks to install
HOOKS=(
    "pre-commit"
    "pre-push"
    "commit-msg"
    "pre-merge-commit"
)

echo "Installing hooks from templates..."
for hook in "${HOOKS[@]}"; do
    SOURCE="$TEMPLATES_DIR/$hook"
    DEST="$HOOKS_DIR/$hook"

    if [ -f "$SOURCE" ]; then
        cp "$SOURCE" "$DEST"
        chmod +x "$DEST"
        echo "  ✓ Installed $hook"
    else
        echo "  ⚠ $hook not found in templates"
    fi
done

echo ""
echo "✅ Git hooks installed successfully!"
echo ""
echo "Hooks enabled:"
echo "  • pre-commit       - Fast checks on every commit"
echo "  • commit-msg       - Enforces Conventional Commits format"
echo "  • pre-push         - Comprehensive checks before pushing to main/develop"
echo "  • pre-merge-commit - Checks before local merge (safety net)"
echo ""
echo "Manual quality check:"
echo "  ./scripts/run-quality-checks.sh"
echo ""
echo "Note: Hooks run automatically. To skip (NOT recommended):"
echo "  git commit --no-verify   # Skip pre-commit & commit-msg"
echo "  git push --no-verify     # Skip pre-push"
echo ""
echo "GitHub Actions also runs quality checks (quality.yml) for every PR/push."

