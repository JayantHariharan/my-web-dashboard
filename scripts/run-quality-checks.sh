#!/bin/bash
# Comprehensive quality & security checks
# Run this manually to verify code before pushing or in CI

set -e

# Default options
JSON_OUTPUT=0
JSON_FILE="quality-report.json"

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --json|-j)
            JSON_OUTPUT=1
            shift
            ;;
        --output|-o)
            JSON_FILE="$2"
            shift 2
            ;;
        --help|-h)
            echo "Usage: $0 [OPTIONS]"
            echo "Run comprehensive quality & security checks"
            echo ""
            echo "Options:"
            echo "  --json, -j        Generate JSON report"
            echo "  --output, -o FILE Specify JSON output file (default: quality-report.json)"
            echo "  --help, -h        Show this help message"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

echo "🔍 Running comprehensive quality & security checks..."
echo ""

# Colors (only use if not JSON output)
if [ $JSON_OUTPUT -eq 0 ]; then
    RED='\033[0;31m'
    GREEN='\033[0;32m'
    YELLOW='\033[1;33m'
    BLUE='\033[0;34m'
    NC='\033[0m'
fi

FAIL=0
WARN=0
CHECKS=()

# Ensure we're in project root
cd "$(dirname "$0")/.." 2>/dev/null || true

# Define check functions with JSON support
check() {
    local name="$1"
    if [ $JSON_OUTPUT -eq 0 ]; then
        echo -e "${BLUE}▶ $name${NC}"
    fi
    CHECKS+=("$name|")
}

pass() {
    local msg="$1"
    if [ $JSON_OUTPUT -eq 0 ]; then
        echo -e "${GREEN}  ✓${NC} $msg"
    fi
    local last_idx=$((${#CHECKS[@]}-1))
    CHECKS[$last_idx]="${CHECKS[$last_idx]}pass:$msg"
}

fail() {
    local msg="$1"
    FAIL=$((FAIL + 1))
    if [ $JSON_OUTPUT -eq 0 ]; then
        echo -e "${RED}  ✗${NC} $msg"
    fi
    local last_idx=$((${#CHECKS[@]}-1))
    CHECKS[$last_idx]="${CHECKS[$last_idx]}fail:$msg"
}

warn() {
    local msg="$1"
    WARN=$((WARN + 1))
    if [ $JSON_OUTPUT -eq 0 ]; then
        echo -e "${YELLOW}  ⚠${NC} $msg"
    fi
    local last_idx=$((${#CHECKS[@]}-1))
    CHECKS[$last_idx]="${CHECKS[$last_idx]}warn:$msg"
}

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
if python -m py_compile src/backend/main.py 2>/dev/null; then
    pass "Syntax valid"
else
    fail "Syntax errors found"
    python -m py_compile src/backend/main.py || true
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
STAGED_PY_FILES=$(git diff --cached --name-only --diff-filter=ACM | grep '\.py$' || true)
if [ -n "$STAGED_PY_FILES" ]; then
    if echo "$STAGED_PY_FILES" | xargs grep -lw -E "TODO|FIXME|BUG|HACK" 2>/dev/null > /dev/null; then
        warn "TODO/FIXME found"
        echo "$STAGED_PY_FILES" | xargs grep -nw -E "TODO|FIXME|BUG|HACK" || true
        echo "  Consider addressing or create issue for tracking."
    else
        pass "No problematic comments found"
    fi
else
    pass "No Python files staged"
fi
echo ""

# 5. Verify documentation timestamps are current
check "Documentation timestamps"
TODAY=$(date +%Y-%m-%d)
OLD_DATES=0
for doc in docs/DEVELOPER.md docs/ARCHITECTURE.md docs/FLYWAY.md docs/MIGRATIONS.md docs/TROUBLESHOOTING.md README.md; do
    if [ -f "$doc" ]; then
        LAST_UPDATED=$(grep -oE 'Last (?:updated|Updated): [0-9]{4}-[0-9]{2}-[0-9]{2}' "$doc" | head -1 || echo "")
        if [ -n "$LAST_UPDATED" ] && [[ ! "$LAST_UPDATED" =~ $TODAY ]]; then
            warn "$doc outdated: $LAST_UPDATED"
            OLD_DATES=1
        fi
    fi
done
if [ $OLD_DATES -eq 0 ]; then
    pass "Documentation dates are current"
else
    warn "Some documentation dates need updating (run pre-commit hook)"
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

# Summary / JSON Output
if [ $JSON_OUTPUT -eq 1 ]; then
    # Build JSON report
    TIMESTAMP=$(date -u +%Y-%m-%dT%H:%M:%SZ)
    JSON_HEADER="{\n  \"scan_metadata\": {\n    \"scanner\": \"Quality Check Script\",\n    \"timestamp\": \"$TIMESTAMP\",\n    \"version\": \"1.0\"\n  },\n  \"checks\": ["

    # Build checks array
    CHECK_JSON=""
    for check in "${CHECKS[@]}"; do
        IFS='|' read -r name result <<< "$check"
        IFS=':' read -r status msg <<< "$result"
        # Escape quotes in message
        msg="${msg//\"/\\\"}"
        if [ -n "$CHECK_JSON" ]; then CHECK_JSON="$CHECK_JSON,"; fi
        CHECK_JSON="$CHECK_JSON\n    {\n      \"name\": \"$name\",\n      \"status\": \"$status\",\n      \"message\": \"$msg\"\n    }"
    done

    PASSED=$(( ${#CHECKS[@]} - FAIL - WARN ))
    JSON_FOOTER="\n  ],\n  \"summary\": {\n    \"total\": ${#CHECKS[@]},\n    \"passed\": $PASSED,\n    \"failed\": $FAIL,\n    \"warnings\": $WARN\n  }\n}"

    echo -e "$JSON_HEADER$CHECK_JSON$JSON_FOOTER" > "$JSON_FILE"
    echo "📊 JSON report written to $JSON_FILE"

    # Exit based on failures
    if [ $FAIL -gt 0 ]; then
        echo "❌ $FAIL check(s) failed"
        exit 1
    else
        echo "✅ All checks passed ($WARN warning(s))"
        exit 0
    fi
else
    # Human-readable output
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
fi
