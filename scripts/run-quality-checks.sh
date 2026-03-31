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

# 2. AI-Powered Comprehensive Quality Scan (replaces black, flake8, mypy, bandit)
check "AI Quality Scan"
if [ -n "$OPENROUTER_API_KEY" ]; then
    if python - <<'PY' 2>/dev/null
import os, sys
sys.path.insert(0, '.github/scripts')
from ai_quality_scan import main
sys.exit(main())
PY
    then
        if [ -f "ai-quality-report.json" ]; then
            # Parse summary
            CRITICAL=$(python -c "import json; print(json.load(open('ai-quality-report.json')).get('summary',{}).get('by_severity',{}).get('Critical',0))" 2>/dev/null || echo "0")
            HIGH=$(python -c "import json; print(json.load(open('ai-quality-report.json')).get('summary',{}).get('by_severity',{}).get('High',0))" 2>/dev/null || echo "0")
            TOTAL=$(python -c "import json; print(json.load(open('ai-quality-report.json')).get('summary',{}).get('total_issues',0))" 2>/dev/null || echo "0")
            STYLE=$(python -c "import json; print(json.load(open('ai-quality-report.json')).get('summary',{}).get('by_category',{}).get('style',0))" 2>/dev/null || echo "0")
            TYPE=$(python -c "import json; print(json.load(open('ai-quality-report.json')).get('summary',{}).get('by_category',{}).get('type',0))" 2>/dev/null || echo "0")
            FORMATTING=$(python -c "import json; print(json.load(open('ai-quality-report.json')).get('summary',{}).get('by_category',{}).get('formatting',0))" 2>/dev/null || echo "0")

            if [ "$CRITICAL" -eq "0" ] && [ "$HIGH" -eq "0" ]; then
                pass "No Critical/High issues (Total: $TOTAL, Style: $STYLE, Type: $TYPE, Format: $FORMATTING)"
            else
                fail "$CRITICAL Critical and $HIGH High issues found (Total: $TOTAL)"
                echo "  Top issues:"
                python -c "import json; issues=sorted(json.load(open('ai-quality-report.json')).get('issues',[]), key=lambda x: {'Critical':4,'High':3,'Medium':2,'Low':1,'Info':0}.get(x.get('severity',''),0), reverse=True); [print(f\"  {i['file']}:{i['line']} - {i['title']}\") for i in issues[:5]]" 2>/dev/null || true
            fi
        else
            warn "No report generated"
        fi
    else
        warn "AI quality scan failed"
    fi
else
    warn "OPENROUTER_API_KEY not set (skipping AI quality scan)"
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
    echo "  - Run manually: ./scripts/run-quality-checks.sh"
    echo "  - Skip (not recommended): git push --no-verify"
    exit 1
fi
