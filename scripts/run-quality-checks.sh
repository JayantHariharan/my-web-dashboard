#!/bin/bash
# Comprehensive quality & security checks
# Run this manually to verify code before pushing or in CI

set -e

echo "🔍 Running comprehensive quality & security checks..."
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

FAIL=0
WARN=0

check() {
    echo -e "${BLUE}▶ $1${NC}"
}

pass() {
    echo -e "${GREEN}  ✓${NC} $1"
}

fail() {
    echo -e "${RED}  ✗${NC} $1"
    FAIL=$((FAIL + 1))
}

warn() {
    echo -e "${YELLOW}  ⚠${NC} $1"
    WARN=$((WARN + 1))
}

# Ensure we're in project root
cd "$(dirname "$0")/.." 2>/dev/null || true

# 1. YAML syntax validation for workflows
check "YAML syntax (workflows)"
if command -v python3 &> /dev/null; then
    YAML_FAIL=0
    # Check all workflow files to catch any syntax errors
    for wf in .github/workflows/*.yml; do
        if [ -f "$wf" ]; then
            if ! python3 -c "import yaml; yaml.safe_load(open('$wf', encoding='utf-8'))" 2>/dev/null; then
                fail "Invalid YAML: $wf"
                YAML_FAIL=1
            fi
        fi
    done
    if [ $YAML_FAIL -eq 0 ]; then
        pass "All workflow YAML files valid"
    fi
else
    warn "python3 not available, skipping YAML validation"
fi
echo ""

# 2. Python syntax
check "Python syntax check"
if python - <<'PY' 2>/dev/null
import ast
from pathlib import Path

for path in Path("src/backend").rglob("*.py"):
    ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
PY
then
    pass "Syntax valid"
else
    fail "Syntax errors found"
    python - <<'PY' || true
import ast
from pathlib import Path

for path in Path("src/backend").rglob("*.py"):
    try:
        ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except SyntaxError as exc:
        print(f"{path}:{exc.lineno}:{exc.offset}: {exc.msg}")
        raise
PY
fi
echo ""

# 3. Hardcoded secrets check
check "Hardcoded secrets"
SECRET_PATTERNS=(
    "SECRET_KEY\s*="
    "PASSWORD\s*="
    "API_KEY\s*="
    "token\s*="
    "ghp_[0-9a-zA-Z]{36}"
    "sk-or-[0-9a-zA-Z]{48}"
    "sk-ant-[0-9a-zA-Z]{32}"
)
FOUND=0
for pattern in "${SECRET_PATTERNS[@]}"; do
    if grep -rn "$pattern" src/backend/ --include="*.py" | grep -v "os.environ" | grep -v "getenv" > /dev/null 2>&1; then
        FOUND=1
        break
    fi
done
if [ $FOUND -eq 0 ]; then
    pass "No obvious hardcoded secrets"
else
    fail "Potential hardcoded secrets found"
    grep -rn "SECRET_KEY\s*=" src/backend/ --include="*.py" | grep -v "os.environ" | grep -v "getenv" || true
fi
echo ""

# 4. Check for TODO/FIXME in committed files
check "No TODO/FIXME in commits"
STAGED_TEXT_FILES=$(git diff --cached --name-only --diff-filter=ACM | grep -E '\.(py|js|html|css|md|yml|yaml|sh)$' || true)
if [ -n "$STAGED_TEXT_FILES" ]; then
    if echo "$STAGED_TEXT_FILES" | xargs grep -lw -E "TODO|FIXME|BUG|HACK" 2>/dev/null > /dev/null; then
        warn "TODO/FIXME found"
        echo "$STAGED_TEXT_FILES" | xargs grep -nw -E "TODO|FIXME|BUG|HACK" || true
        echo "  Consider addressing or create issue for tracking."
    else
        pass "No problematic comments found"
    fi
else
    pass "No tracked text files staged"
fi
echo ""

# 5. README present (single source of project docs)
check "README.md"
if [ -f README.md ]; then
    pass "README.md exists"
else
    fail "README.md missing"
fi
echo ""

# 6. Database migration check
check "Database migrations"
if ls flyway/sql/V*.sql > /dev/null 2>&1; then
    pass "Migrations exist ($(ls flyway/sql/V*.sql | wc -l) files)"
else
    warn "No migration files found"
fi
echo ""

# Summary
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
if [ $FAIL -eq 0 ] && [ $WARN -eq 0 ]; then
    echo -e "${GREEN}✅ All checks passed!${NC}"
    echo ""
    echo "Your code is ready to push. All quality standards met."
    exit 0
elif [ $FAIL -eq 0 ]; then
    echo -e "${YELLOW}⚠️  Checks passed with $WARN warning(s)${NC}"
    echo ""
    echo "Review the warnings above. They're not blocking but worth checking."
    exit 0
else
    echo -e "${RED}❌ $FAIL check(s) failed.${NC}"
    echo ""
    echo "Fix the errors above before pushing."
    echo ""
    echo "💡 Tips:"
    echo "  - Run manually: ./scripts/run-quality-checks.sh"
    echo "  - Skip (not recommended): git push --no-verify"
    exit 1
fi
