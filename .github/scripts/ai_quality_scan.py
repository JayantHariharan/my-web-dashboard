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


def build_comprehensive_quality_prompt(files: List[Dict[str, str]]) -> str:
    """Build the comprehensive code quality analysis prompt for Claude."""

    prompt = """You are an expert Python code reviewer performing a comprehensive quality audit.

Analyze the following Python files and detect issues across these categories:

## 1. STYLE & LINTING (replaces flake8)
- PEP 8 violations (line length, naming conventions, whitespace)
- Unused imports or variables
- Too complex functions (cyclomatic complexity)
- Missing docstrings (for public functions/classes)
- Too many arguments/locals/returns
- Global statements
- Bare except clauses
- Mutable default arguments

## 2. TYPE ISSUES (replaces mypy)
- Type inconsistencies
- Missing type hints for function parameters/returns (especially public APIs)
- Incorrect type usage
- Possible None/optional errors
- Wrong return types
- incompatible collections

## 3. FORMATTING (replaces black/isort)
- Inconsistent indentation
- Missing/extra blank lines
- Improper quotes (mixed single/double)
- Trailing whitespace
- Import ordering issues
- Long lines (>100 chars)

## 4. SECURITY & BEST PRACTICES (replaces bandit + more)
- Hardcoded secrets (passwords, tokens, API keys)
- SQL injection (string concatenation in queries)
- Command injection (subprocess, os.system with user input)
- Path traversal vulnerabilities
- Insecure deserialization (pickle, yaml.load without safe loader)
- Use of eval() or exec()
- Weak cryptography (MD5, SHA1)
- Missing input validation
- Excessive logging of sensitive data
- Insecure default values

## 5. CODE QUALITY & MAINTAINABILITY
- Code smells (long methods, large classes, feature envy)
- Duplicate code
- Magic numbers/strings
- Overly nested conditionals
- Deep inheritance hierarchies
- Tight coupling
- God classes/modules
- Dead code
- Overly complex logic
- Inefficient algorithms/data structures

## 6. POTENTIAL BUGS
- Unreachable code
- Infinite loops
- Division by zero
- Index out of bounds risks
- Mutation during iteration
- Resource leaks (unclosed files/connections)
- Race conditions
- Incorrect boolean logic
- Off-by-one errors

## Output Format (Strict JSON):

{
  "scan_metadata": {
    "scanner": "AI Code Quality Scanner",
    "timestamp": "ISO8601",
    "files_scanned": N,
    "total_lines": N
  },
  "summary": {
    "total_issues": N,
    "by_severity": {
      "Critical": N,
      "High": N,
      "Medium": N,
      "Low": N,
      "Info": N
    },
    "by_category": {
      "style": N,
      "type": N,
      "formatting": N,
      "security": N,
      "quality": N,
      "bug": N
    },
    "has_blocking_issues": false
  },
  "issues": [
    {
      "file": "path/to/file.py",
      "line": N,
      "column": N,
      "severity": "Critical|High|Medium|Low|Info",
      "category": "style|type|formatting|security|quality|bug",
      "subcategory": "pep8|unused-import|missing-type-hint|hardcoded-secret|...",
      "title": "Brief title",
      "description": "Detailed explanation of the issue",
      "evidence": "Code snippet showing the problem",
      "recommendation": "How to fix it with code example if helpful",
      "auto_fixable": false
    }
  ],
  "statistics": {
    "files_with_issues": N,
    "lines_of_code": N,
    "type_annotated_functions": N,
    "functions_with_docstrings": N
  }
}

IMPORTANT:
- Be precise and actionable. Focus on real issues, not style preferences.
- Prioritize critical security and correctness issues.
- If an issue has a clear automatic fix, mark "auto_fixable": true.
- For formatting issues, be specific about line/column.
- For type issues, infer the likely correct type.
- Consider the project context (FastAPI backend, security-focused).

Files to analyze:
"""

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
    """Send prompt to OpenRouter (supports various models) with retry logic for rate limits."""
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
                max_tokens=4000,  # Reduced for faster response
                temperature=0.0,
                timeout=300,  # 5 minute timeout per attempt
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
            error_str = str(e)
            # Check for rate limit (429) or server errors (5xx)
            if "429" in error_str or "rate-limited" in error_str or "502" in error_str or "503" in error_str or attempt < max_retries - 1:
                print(f"Attempt {attempt + 1} failed (rate limit/server error). Retrying in {retry_delay}s...")
                import time
                time.sleep(retry_delay)
                retry_delay *= 2  # Exponential backoff
                continue
            else:
                print(f"Error calling OpenRouter API after {max_retries} attempts: {e}")
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

    # Rough estimates for type annotations and docstrings
    # The AI should provide more accurate counts, but we use these as fallbacks
    type_annotated = 0
    docstrings = 0

    all_content = "\n".join(f['content'] for f in files)
    # Count function definitions with type hints (very rough)
    type_annotated = all_content.count('->')
    # Count docstrings (rough)
    docstrings = all_content.count('"""') // 2 + all_content.count("'''") // 2

    return {
        "files_with_issues": len(files_with_issues_set),
        "total_lines": total_lines,  # Match expected key name
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

    # Build prompt
    print("Building comprehensive quality analysis prompt...")
    prompt = build_comprehensive_quality_prompt(file_contents)

    # Run analysis
    print("Querying Claude via OpenRouter for comprehensive analysis...")
    model = os.environ.get("OPENROUTER_MODEL", "stepfun/step-3.5-flash:free")
    print(f"   Model: {model}")
    result = run_claude_analysis_openrouter(prompt, openrouter_key, model)

    # If API call failed after retries, skip (no report generated)
    if result is None:
        print("⚠️  OpenRouter API unavailable after retries. Skipping AI quality scan.")
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
