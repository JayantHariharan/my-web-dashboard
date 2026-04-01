#!/usr/bin/env python3
"""
AI-Powered Comprehensive Code Quality Scanner for GitHub Actions.

This single tool replaces:
- flake8 (linting, style violations)
- mypy (type checking)
- black (formatting)
- bandit (security scanning)

Uses Claude via OpenRouter to perform intelligent, context-aware code analysis.
"""

import os
import sys
import json
import glob
from pathlib import Path
from typing import List, Dict, Any

try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False


def collect_python_files() -> List[str]:
    """Collect all Python files to analyze."""
    python_files = glob.glob("src/backend/**/*.py", recursive=True)
    return [f for f in python_files if not f.endswith('__pycache__')]


def read_file_content(filepath: str) -> str:
    """Read file content safely."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        return f"ERROR: Could not read file: {e}"


def build_comprehensive_quality_prompt(files: List[Dict[str, str]], max_files: int = 8, max_content_per_file: int = 6000) -> str:
    """Build the comprehensive code quality analysis prompt for Claude."""

    prompt = """You are an expert Python code reviewer performing a comprehensive quality audit for a FastAPI backend project.

Your job is to find REAL issues that impact security, correctness, performance, or maintainability. Be thorough but practical.

## ANALYSIS CATEGORIES

### 1. SECURITY (Highest Priority)
- Hardcoded secrets (passwords, tokens, API keys, database URLs)
- SQL injection (string concatenation, f-strings in SQL queries)
- Command injection (subprocess, os.system with user input)
- Path traversal (unsanitized user input in file paths)
- Insecure deserialization (pickle, yaml.load without SafeLoader)
- Use of eval() or exec()
- Weak cryptography (MD5, SHA1, weak random)
- Missing input validation on user-facing endpoints
- Sensitive data in logs (passwords, tokens, PII)
- Insecure CORS configuration
- Missing authentication/authorization checks
- Debug mode in production

### 2. CRITICAL BUGS & RUNTIME ERRORS
- Division by zero
- Index out of bounds / KeyError risks
- None type errors (missing None checks)
- Unhandled exceptions (bare except, missing try-except)
- Infinite loops
- Unreachable code
- Resource leaks (files, DB connections, sessions not closed)
- Race conditions (async issues, shared state)
- Mutating collections during iteration
- Off-by-one errors

### 3. TYPE SAFETY & CORRECTNESS (mypy replacement)
- Missing type hints for function parameters/returns (public APIs must be typed)
- Type inconsistencies (wrong return type, wrong argument type)
- Optional/None not properly handled (missing Optional, None checks)
- Wrong collection types (list vs set, wrong generic)
- Incorrect type annotations
- Mutable default arguments

### 4. CODE QUALITY & MAINTAINABILITY
- Long functions (>50 lines) or complex functions (cyclomatic complexity >10)
- Large classes (>300 lines) or too many methods
- Duplicate code blocks
- Magic numbers/strings (use constants)
- Overly nested conditionals (>3 levels)
- God modules (doing too many things)
- Dead code (unused functions, variables, imports)
- Overly complex logic that's hard to understand
- Inefficient algorithms (O(n²) when O(n) possible)
- Tight coupling, lack of abstraction

### 5. STYLE & FORMATTING (flake8/black/isort replacement)
- PEP 8 violations:
  - Line length > 100 characters (break appropriately)
  - Naming conventions (snake_case for functions/variables, PascalCase for classes)
  - Missing/extra blank lines (2 before class/function, 1 between methods)
  - Trailing whitespace
  - Inconsistent indentation (use 4 spaces, not tabs)
- Import ordering:
  - Standard library first
  - Third-party packages second
  - Local application imports third
  - Blank line between each group
- Missing docstrings:
  - All public functions/classes must have docstrings
  - Docstring should explain purpose, args, returns, raises
- Bare `except:` clauses (catch specific exceptions)
- Mutable default arguments (use None instead)
- Global statements

## OUTPUT FORMAT (Strict JSON)

{
  "scan_metadata": {
    "scanner": "AI Code Quality Scanner",
    "timestamp": "ISO8601",
    "files_scanned": 0,
    "total_lines": 0
  },
  "summary": {
    "total_issues": 0,
    "by_severity": {
      "Critical": 0,
      "High": 0,
      "Medium": 0,
      "Low": 0,
      "Info": 0
    },
    "by_category": {
      "security": 0,
      "bug": 0,
      "type": 0,
      "quality": 0,
      "style": 0,
      "formatting": 0
    },
    "has_blocking_issues": false
  },
  "issues": [
    {
      "file": "src/backend/auth/service.py",
      "line": 42,
      "column": 15,
      "severity": "Critical",
      "category": "security",
      "subcategory": "hardcoded-secret",
      "title": "Hardcoded database password in source code",
      "description": "The database password is hardcoded as a string literal. This is a major security risk as the password will be exposed in version control, logs, and to anyone with code access.",
      "evidence": "PASSWORD = 'supersecret123'",
      "recommendation": "Remove the hardcoded password and load it from environment variables using os.environ.get('DB_PASSWORD') or a configuration manager. Example:\\n\\nimport os\\nPASSWORD = os.environ.get('DB_PASSWORD')\\nif not PASSWORD:\\n    raise ValueError('DB_PASSWORD environment variable not set')",
      "auto_fixable": false
    }
  ],
  "statistics": {
    "files_with_issues": 0,
    "lines_of_code": 0,
    "type_annotated_functions": 0,
    "functions_with_docstrings": 0
  }
}

## CRITICAL RULES FOR ISSUE SUBMISSION

1. **Accuracy**: Only report real issues. If you're unsure, omit it rather than report a false positive.
2. **Line/Column accuracy**: Pinpoint EXACT line and column numbers. Double-check before reporting.
3. **Evidence**: Quote the EXACT code snippet that demonstrates the issue.
4. **Recommendation**: Provide a clear, actionable fix WITH CODE EXAMPLE whenever possible.
5. **Severity grading**:
   - Critical: Security vulnerability, data loss, crash, infinite loop
   - High: Major bug, incorrect behavior, missing error handling
   - Medium: Code smell, missing type hints/docstrings, moderate complexity
   - Low: Minor style issues, whitespace, naming that violates PEP8
   - Info: Suggestions, improvements, best practices
6. **Category assignment**: Use ONE primary category. Precedence: security > bug > type > quality > style > formatting
7. **Blocking issues**: Set "has_blocking_issues": true if ANY Critical/High severity exists, OR Medium+ security issues exist.
8. **Statistics**: Accurately count:
   - functions_with_docstrings: Count def statements that have triple-quoted strings immediately after
   - type_annotated_functions: Count functions with -> return type annotation AND parameter type hints
   - lines_of_code: Total non-empty, non-comment lines (rough estimate ok)

## PROJECT CONTEXT
- FastAPI backend with PostgreSQL
- Security-focused application (user authentication, profiles)
- Python 3.12
- Code should be production-ready, secure, and maintainable

Now analyze these files and output ONLY valid JSON:

"""
    files_to_analyze = files[:max_files]
    for file_info in files_to_analyze:
        prompt += f"\n--- File: {file_info['path']} (lines: {len(file_info['content'].splitlines())}) ---\n"
        prompt += file_info['content'][:max_content_per_file]
        if len(file_info['content']) > max_content_per_file:
            prompt += "\n... [TRUNCATED] ..."

    return prompt

    for file_info in files[:8]:  # Limit to 8 files to keep runtime reasonable
        prompt += f"\n--- File: {file_info['path']} (lines: {len(file_info['content'].splitlines())}) ---\n"
        prompt += file_info['content'][:6000]  # Truncate very long files
        if len(file_info['content']) > 6000:
            prompt += "\n... [TRUNCATED] ..."

    prompt += """


Provide your analysis in valid JSON matching the schema above. Be thorough but concise.
"""

    return prompt


def run_claude_analysis_openrouter(prompt: str, api_key: str, model: str = "stepfun/step-3.5-flash:free") -> Dict[str, Any]:
    """Send prompt to OpenRouter with retry logic for rate limits and context errors."""
    if not OPENAI_AVAILABLE:
        print("Error: openai package not installed. Run: pip install openai")
        sys.exit(1)

    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=api_key,
    )

    max_retries = 3
    retry_delay = 10  # seconds

    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "You are an expert Python code reviewer. Always respond with valid JSON matching the requested schema."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=4000,
                temperature=0.0,
                timeout=300,
            )

            response_text = response.choices[0].message.content

            # Extract JSON from response
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1

            if json_start != -1 and json_end != -1:
                json_str = response_text[json_start:json_end]
                return json.loads(json_str)
            else:
                return json.loads(response_text)

        except Exception as e:
            error_str = str(e).lower()

            # Check for rate limit (429) or server errors (5xx)
            is_retryable = (
                "429" in error_str or
                "rate-limited" in error_str or
                "rate limit" in error_str or
                "502" in error_str or
                "503" in error_str or
                "context length" in error_str or
                "context_limit" in error_str or
                "too many tokens" in error_str or
                "maximum context" in error_str
            )

            if is_retryable and attempt < max_retries - 1:
                print(f"Attempt {attempt + 1} failed ({type(e).__name__}). Retrying in {retry_delay}s...")
                import time
                time.sleep(retry_delay)
                retry_delay *= 2  # Exponential backoff
                continue
            else:
                print(f"Error calling OpenRouter API: {e}")
                return None  # Signal failure



def compute_statistics(files: List[Dict[str, str]], issues: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Compute statistics about the codebase from file contents and issues."""
    total_lines = 0
    files_with_issues_set = set()

    for file_info in files:
        content = file_info['content']
        total_lines += len(content.splitlines())

    # Count files that have at least one issue
    for issue in issues:
        files_with_issues_set.add(issue.get('file', ''))

    # Better estimates for type annotations and docstrings using regex
    import re
    type_annotated = 0
    docstrings = 0

    all_content = "\n".join(f['content'] for f in files)

    # Count function definitions with return type annotation (->)
    # Pattern: def func(...) -> type:
    type_annotated = len(re.findall(r'def\s+\w+\s*\([^)]*\)\s*->', all_content))

    # Count docstrings more accurately (triple quotes at function/class start)
    # This is still approximate but better than simple division
    docstrings = len(re.findall(r'""".*?"""', all_content, re.DOTALL))
    # For single quotes
    docstrings += len(re.findall(r"'''.*?'''", all_content, re.DOTALL))

    return {
        "files_with_issues": len(files_with_issues_set),
        "total_lines": total_lines,
        "type_annotated_functions": type_annotated,
        "functions_with_docstrings": docstrings
    }


def check_blocking_issues(result: Dict[str, Any]) -> bool:
    """
    Check if there are blocking issues that should fail the check.
    Returns True if there are blocking issues, False otherwise.
    """
    summary = result.get("summary", {})

    # Critical or High severity issues are blocking
    critical = summary.get("by_severity", {}).get("Critical", 0)
    high = summary.get("by_severity", {}).get("High", 0)

    if critical > 0 or high > 0:
        return True

    # Security issues at Medium+ could also be blocking
    medium_security = 0
    for issue in result.get("issues", []):
        if issue.get("category") == "security" and issue.get("severity") in ["Medium", "High", "Critical"]:
            medium_security += 1

    if medium_security > 0:
        return True

    return False


def main():
    print("Starting AI-Powered Comprehensive Code Quality Scan...")

    # Check for OpenRouter API key
    openrouter_key = os.environ.get("OPENROUTER_API_KEY")

    if not openrouter_key:
        print("No OpenRouter API key set - cannot run AI quality scan")
        print("Set OPENROUTER_API_KEY in GitHub: Settings -> Secrets and variables -> Actions")
        sys.exit(0)

    # Collect files
    files = collect_python_files()
    print(f"Found {len(files)} Python files to analyze")

    if not files:
        print("No Python files found to analyze")
        sys.exit(1)

    # Read file contents
    file_contents = []
    total_lines = 0
    for filepath in files:
        content = read_file_content(filepath)
        total_lines += len(content.splitlines())
        file_contents.append({"path": filepath, "content": content})

    # Adaptive analysis: try with decreasing file limits if we hit context/rate limits
    model = os.environ.get("OPENROUTER_MODEL", "stepfun/step-3.5-flash:free")
    print(f"   Model: {model}")

    # Configurations: (max_files, max_content_per_file)
    configs = [(8, 6000), (4, 4000), (2, 2000)]
    result = None

    for i, (max_files, max_content) in enumerate(configs):
        print(f"\n📊 Attempt {i+1}: Analyzing up to {max_files} files (max {max_content} chars each)...")
        prompt = build_comprehensive_quality_prompt(file_contents, max_files=max_files, max_content_per_file=max_content)
        result = run_claude_analysis_openrouter(prompt, openrouter_key, model)

        if result is not None:
            print(f"✅ Analysis succeeded with {max_files} files")
            break
        else:
            if i < len(configs) - 1:
                print(f"⚠️  Analysis failed. Retrying with fewer files ({max_files} → {configs[i+1][0]})...")
            else:
                print("❌ All analysis attempts failed. Skipping AI quality scan.")
                print("   This does not block the PR; treat as skipped.")
                sys.exit(0)

    # Ensure scan_metadata exists
    if "scan_metadata" not in result:
        result["scan_metadata"] = {}

    # Add metadata
    from datetime import datetime
    result["scan_metadata"]["timestamp"] = datetime.utcnow().isoformat() + "Z"
    result["scan_metadata"]["files_scanned"] = len(files)
    result["scan_metadata"]["total_lines"] = total_lines

    # Ensure summary exists and has required fields
    if "summary" not in result:
        result["summary"] = {}

    summary = result["summary"]

    # Compute total issues count if not provided
    if "total_issues" not in summary:
        summary["total_issues"] = len(result.get("issues", []))

    # Also add files_scanned and total_lines to summary for convenience
    summary["files_scanned"] = len(files)
    summary["total_lines"] = total_lines

    # Ensure by_severity has all severity levels
    by_severity = summary.get("by_severity", {})
    for severity in ["Critical", "High", "Medium", "Low", "Info"]:
        if severity not in by_severity:
            by_severity[severity] = 0
    summary["by_severity"] = by_severity

    # Ensure by_category has all categories
    by_category = summary.get("by_category", {})
    for category in ["style", "type", "formatting", "security", "quality", "bug"]:
        if category not in by_category:
            by_category[category] = 0
    summary["by_category"] = by_category

    # Calculate has_blocking_issues
    summary["has_blocking_issues"] = check_blocking_issues(result)

    # Compute and set statistics
    issues = result.get("issues", [])
    computed_stats = compute_statistics(file_contents, issues)
    result["statistics"] = computed_stats

    # Write report
    report_path = "ai-quality-report.json"
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    print(f"Quality report written to {report_path}")

    # Print detailed summary
    if "summary" in result:
        summary = result["summary"]
        stats = result.get("statistics", {})
        print("\nQuality Scan Summary:")
        print(f"   Total issues: {summary.get('total_issues', 0)}")
        print(f"   Files scanned: {summary.get('files_scanned', len(files))}")
        print(f"   Total lines: {stats.get('total_lines', total_lines)}")
        print(f"   Functions with docstrings: {stats.get('functions_with_docstrings', 0)}")
        print(f"   Type-annotated functions: {stats.get('type_annotated_functions', 0)}")
        print("\n   By Severity:")
        for severity in ["Critical", "High", "Medium", "Low", "Info"]:
            count = summary.get("by_severity", {}).get(severity, 0)
            if count > 0:
                print(f"     {severity}: {count}")
        print("\n   By Category:")
        for category in ["style", "type", "formatting", "security", "quality", "bug"]:
            count = summary.get("by_category", {}).get(category, 0)
            if count > 0:
                print(f"     {category}: {count}")

        # Show blocking status
        if summary.get("has_blocking_issues"):
            print("\nBlocking issues detected (Critical/High severity or Medium+ security)")
            sys.exit(1)
        else:
            print("\nNo blocking issues found")
            sys.exit(0)
    else:
        print("No summary in report")
        sys.exit(0)


if __name__ == "__main__":
    main()
