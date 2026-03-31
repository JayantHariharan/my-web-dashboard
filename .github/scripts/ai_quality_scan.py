#!/usr/bin/env python3
"""
AI-Powered Comprehensive Code Quality Scanner for GitHub Actions.

This single tool replaces:
- flake8 (linting, style violations)
- mypy (type checking)
- black (formatting)
- bandit (security scanning)

Uses Claude to perform intelligent, context-aware code analysis.
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

    for file_info in files[:15]:  # Limit to 15 files for context window
        prompt += f"\n--- File: {file_info['path']} (lines: {len(file_info['content'].splitlines())}) ---\n"
        prompt += file_info['content'][:12000]  # Truncate very long files
        if len(file_info['content']) > 12000:
            prompt += "\n... [TRUNCATED] ..."

    prompt += """


Provide your analysis in valid JSON matching the schema above. Be thorough but concise.
"""

    return prompt



def run_claude_analysis_openrouter(prompt: str, api_key: str, model: str = "anthropic/claude-3-opus") -> Dict[str, Any]:
    """Send prompt to OpenRouter (supports various models)."""
    if not OPENAI_AVAILABLE:
        print("Error: openai package not installed. Run: pip install openai")
        sys.exit(1)

    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=api_key,
    )

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are an expert Python code reviewer. Always respond with valid JSON matching the requested schema."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=8000,
            temperature=0.0,
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
        print(f"Error calling OpenRouter API: {e}")
        return {
            "error": str(e),
            "scan_metadata": {
                "scanner": "AI Code Quality Scanner",
                "status": "failed"
            }
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
    print("🚀 Starting AI-Powered Comprehensive Code Quality Scan...")

    # Check for OpenRouter API key
    openrouter_key = os.environ.get("OPENROUTER_API_KEY")

    if not openrouter_key:
        print("⚠️  No OpenRouter API key set - cannot run AI quality scan")
        print("Set OPENROUTER_API_KEY in GitHub: Settings → Secrets and variables → Actions")
        sys.exit(0)

    # Collect files
    files = collect_python_files()
    print(f"📁 Found {len(files)} Python files to analyze")

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
    print("🧠 Building comprehensive quality analysis prompt...")
    prompt = build_comprehensive_quality_prompt(file_contents)

    # Run analysis
    print("🤖 Querying Claude via OpenRouter for comprehensive analysis...")
    model = os.environ.get("OPENROUTER_MODEL", "anthropic/claude-3-opus")
    print(f"   Model: {model}")
    result = run_claude_analysis_openrouter(prompt, openrouter_key, model)

    # Add metadata
    from datetime import datetime
    result["scan_metadata"]["timestamp"] = datetime.utcnow().isoformat() + "Z"
    result["scan_metadata"]["files_scanned"] = len(files)
    result["scan_metadata"]["total_lines"] = total_lines

    # Ensure summary exists
    if "summary" not in result:
        result["summary"] = {}

    # Calculate has_blocking_issues
    result["summary"]["has_blocking_issues"] = check_blocking_issues(result)

    # Write report
    report_path = "ai-quality-report.json"
    with open(report_path, 'w') as f:
        json.dump(result, f, indent=2)

    print(f"✅ Quality report written to {report_path}")

    # Print detailed summary
    if "summary" in result:
        summary = result["summary"]
        print("\n📊 Quality Scan Summary:")
        print(f"   Total issues: {summary.get('total_issues', 0)}")
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
            print("\n❌ Blocking issues detected (Critical/High severity or Medium+ security)")
            sys.exit(1)
        else:
            print("\n✅ No blocking issues found")
            sys.exit(0)
    else:
        print("⚠️  No summary in report")
        sys.exit(0)


if __name__ == "__main__":
    main()
