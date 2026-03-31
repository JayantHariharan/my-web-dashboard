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

# 1. Python syntax
check "Python syntax check"
if python -m py_compile src/backend/main.py 2>/dev/null; then
    pass "Syntax valid"
else
    fail "Syntax errors found"
    python -m py_compile src/backend/main.py || true
fi
echo ""

# 2. Black formatting
check "Code formatting (black)"
if command -v black &> /dev/null; then
    if black --check src/backend/ 2>/dev/null; then
        pass "Code properly formatted"
    else
        fail "Code needs formatting"
        echo "  Run: black src/backend/"
    fi
else
    warn "black not installed (pip install black)"
fi
echo ""

# 3. Flake8 linting
check "Linting (flake8)"
if command -v flake8 &> /dev/null; then
    if flake8 src/backend/ --isolated > /dev/null 2>&1; then
        pass "No lint errors"
    else
        fail "Lint errors found"
        echo "  Critical errors:"
        flake8 src/backend/ --count --select=E9,F63,F7,F82 --show-source --isolated || true
    fi
else
    warn "flake8 not installed (pip install flake8)"
fi
echo ""

# 4. Mypy type checking
check "Type checking (mypy)"
if command -v mypy &> /dev/null; then
    if mypy src/backend/main.py --ignore-missing-imports 2>/dev/null; then
        pass "No type errors"
    else
        warn "Type errors found (checking)"
        mypy src/backend/main.py --ignore-missing-imports || true
    fi
else
    warn "mypy not installed (pip install mypy)"
fi
echo ""

# 5. Bandit security scan
check "Security scan (bandit)"
if command -v bandit &> /dev/null; then
    if bandit -r src/backend/ -f json -o /tmp/bandit-report.json 2>/dev/null; then
        # Use Python to parse JSON (no jq dependency)
        HIGH_CRITICAL=$(python -c "import json; print(sum(1 for i in json.load(open('/tmp/bandit-report.json')) if i.get('issue_severity') in ('High','Critical')))" 2>/dev/null || echo "0")
        MEDIUM=$(python -c "import json; print(sum(1 for i in json.load(open('/tmp/bandit-report.json')) if i.get('issue_severity') == 'Medium'))" 2>/dev/null || echo "0")
        if [ "$HIGH_CRITICAL" -eq "0" ]; then
            pass "No High/Critical issues (${MEDIUM} Medium)"
        else
            fail "$HIGH_CRITICAL High/Critical issues found"
            echo "  Top issues:"
            python -c "import json; [print(f\"  {i['filename']}:{i['line_number']} - {i['issue_text']}\") for i in json.load(open('/tmp/bandit-report.json')) if i.get('issue_severity') in ('High','Critical')][:10]" 2>/dev/null || true
        fi
    else
        warn "Bandit scan failed"
    fi
else
    warn "bandit not installed (pip install bandit)"
fi
echo ""

# 6. AI Security Analysis (if OpenRouter key available)
check "AI Security Analysis (OpenRouter)"
if [ -n "$OPENROUTER_API_KEY" ]; then
    if python .github/scripts/claude_security_scan.py 2>/dev/null; then
        if [ -f "claude-security-report.json" ]; then
            CRITICAL=$(python -c "import json; print(json.load(open('claude-security-report.json')).get('summary',{}).get('by_severity',{}).get('Critical',0))" 2>/dev/null || echo "0")
            HIGH=$(python -c "import json; print(json.load(open('claude-security-report.json')).get('summary',{}).get('by_severity',{}).get('High',0))" 2>/dev/null || echo "0")
            TOTAL=$(python -c "import json; print(json.load(open('claude-security-report.json')).get('summary',{}).get('total_issues',0))" 2>/dev/null || echo "0")
            if [ "$CRITICAL" -eq "0" ] && [ "$HIGH" -eq "0" ]; then
                pass "No Critical/High issues (Total: $TOTAL)"
            else
                fail "$CRITICAL Critical and $HIGH High issues found"
                echo "  See claude-security-report.json for details"
            fi
        else
            warn "No report generated"
        fi
    else
        warn "Analysis failed"
    fi
else
    warn "OPENROUTER_API_KEY not set (skipping AI analysis)"
    echo "  Set env var or add secret to enable this check."
fi
echo ""

# 7. Check for secrets in code
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

# 8. Verify documentation timestamps are current
check "Documentation timestamps"
TODAY=$(date +%Y-%m-%d)
OLD_DATES=0
for doc in docs/DEVELOPER.md docs/ARCHITECTURE.md docs/FLYWAY.md docs/MIGRATIONS.md; do
    if [ -f "$doc" ]; then
        LAST_UPDATED=$(grep -oE 'Last (?:updated|Updated): [0-9]{4}-[0-9]{2}-[0-9]{2}' "$doc" | head -1 || echo "")
        if [ -n "$LAST_UPDATED" ] && [[ ! "$LAST_UPDATED" =~ $TODAY ]]; then
            echo -e "${YELLOW}  ⚠ $doc: $LAST_UPDATED${NC}"
            OLD_DATES=1
        fi
    fi
done
if [ $OLD_DATES -eq 0 ]; then
    pass "Documentation dates are current"
else
    warn "Some documentation dates may need updating"
fi
echo ""

# 9. Database migration check
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
    echo "  - Format code: black src/backend/"
    echo "  - Run manually: ./scripts/run-quality-checks.sh"
    echo "  - Skip (not recommended): git push --no-verify"
    exit 1
fi
