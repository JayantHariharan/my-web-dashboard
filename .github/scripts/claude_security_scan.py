#!/usr/bin/env python3
"""
Claude-powered security scanner for GitHub Actions.

Analyzes Python code for security vulnerabilities, secrets, and code quality issues.
Supports both Anthropic API and OpenRouter proxy.
"""

import os
import sys
import json
import glob
from pathlib import Path
from typing import List, Dict, Any

try:
    from anthropic import Anthropic
except ImportError:
    print("Error: anthropic package not installed. Run: pip install anthropic")
    sys.exit(1)

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


def build_security_prompt(files: List[Dict[str, str]]) -> str:
    """Build the security analysis prompt for Claude."""

    prompt = """You are a security expert performing a comprehensive security audit of a Python codebase, with special attention to detecting malicious code that could exfiltrate secrets.

Analyze the following files for security vulnerabilities, secrets, and code quality issues.

## Priority 1: Detect Potential Secret Exfiltration / Malicious Code

Look for patterns that could indicate malicious PRs trying to steal secrets:

1. **Environment variable access combined with network transmission**:
   - Code that reads `os.environ`, `os.getenv()`, or environment variables AND then sends them via HTTP requests, sockets, or logging
   - Example: `requests.post(url, json={'secrets': os.environ})`

2. **Direct printing/logging of sensitive data**:
   - `print(os.environ)` or `logger.info(os.getenv('SECRET_KEY'))`
   - Sending sensitive data to external URLs

3. **File operations on sensitive files**:
   - Reading `.env`, `config.json`, `secrets.json`, credential files
   - Uploading these files to external servers

4. **Suspicious imports and usage**:
   - `paramiko` (SSH), `ftplib` (FTP) - could be used to exfiltrate data
   - Base64 encoding before transmission
   - Compressing/sending entire directories

5. **Command execution with environment data**:
   - `subprocess` or `os.system` with environment variables
   - `eval()` or `exec()` with user-controlled or environment data

## Priority 2: Standard Security Vulnerabilities

6. Hardcoded secrets (API keys, passwords, tokens, SECRET_KEY)
7. SQL injection vulnerabilities (raw SQL concatenation, missing parameterization)
8. Command injection (subprocess calls, os.system, eval, exec)
9. XSS vulnerabilities (in web context)
10. Insecure direct object references
11. Authentication bypass issues
12. Rate limiting weaknesses
13. Cryptographic failures (weak algorithms, hardcoded salts)
14. Error message information leakage
15. Input validation issues
16. Insecure deserialization
17. Session management issues
18. Race conditions
19. Path traversal vulnerabilities
20. Use of deprecated/insecure functions

## Output Format (JSON):

{
  "scan_metadata": {
    "scanner": "Claude Security Scanner",
    "timestamp": "ISO8601",
    "files_scanned": N
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
      "exfiltration": N,
      "hardcoded-secret": N,
      "sql-injection": N,
      ...
    }
  },
  "findings": [
    {
      "file": "path/to/file.py",
      "line": N,
      "severity": "Critical|High|Medium|Low|Info",
      "category": "exfiltration|hardcoded-secret|sql-injection|command-injection|xss|...",
      "title": "Brief title",
      "description": "Detailed description",
      "evidence": "Specific code snippet showing the issue",
      "recommendation": "How to fix"
    }
  ]
}

Be EXTRA vigilant for subtle exfiltration attempts (e.g., environment variables sent indirectly, dataencoded before transmission).

Files to analyze:
"""

    for file_info in files[:10]:  # Limit to first 10 files to stay within context
        prompt += f"\n--- File: {file_info['path']} ---\n"
        prompt += file_info['content'][:8000]  # Truncate very long files
        if len(file_info['content']) > 8000:
            prompt += "\n... [TRUNCATED] ..."

    prompt += "\n\nProvide your analysis in the specified JSON format. Be thorough but concise."

    return prompt


def run_claude_analysis_anthropic(prompt: str, api_key: str) -> Dict[str, Any]:
    """Send prompt to Claude via Anthropic API."""
    client = Anthropic(api_key=api_key)

    try:
        message = client.messages.create(
            model="claude-opus-4-20250515",  # Use latest Claude model
            max_tokens=4000,
            temperature=0.0,  # Deterministic for security scanning
            system="You are a security expert performing static code analysis. Always respond with valid JSON matching the requested schema.",
            messages=[
                {"role": "user", "content": prompt}
            ]
        )

        response_text = message.content[0].text

        # Extract JSON from response (Claude might add markdown formatting)
        json_start = response_text.find('{')
        json_end = response_text.rfind('}') + 1

        if json_start != -1 and json_end != -1:
            json_str = response_text[json_start:json_end]
            return json.loads(json_str)
        else:
            # Fallback: try to parse the whole response
            return json.loads(response_text)

    except Exception as e:
        print(f"Error calling Anthropic API: {e}")
        return {
            "error": str(e),
            "scan_metadata": {
                "scanner": "Claude Security Scanner",
                "status": "failed"
            }
        }


def run_claude_analysis_openrouter(prompt: str, api_key: str, model: str = "meta-llama/llama-3.3-70b-instruct") -> Dict[str, Any]:
    """Send prompt to OpenRouter (supports various models including free ones)."""
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
                {"role": "system", "content": "You are a security expert performing static code analysis. Always respond with valid JSON matching the requested schema."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=4000,
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
                "scanner": "Claude Security Scanner",
                "status": "failed"
            }
        }


def main():
    print("🔍 Starting Claude-powered security scan...")

    # Check for OpenRouter API key
    openrouter_key = os.environ.get("OPENROUTER_API_KEY")

    if not openrouter_key:
        print("⚠️  No OpenRouter API key set - skipping Claude analysis")
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
    for filepath in files:
        content = read_file_content(filepath)
        file_contents.append({"path": filepath, "content": content})

    # Build prompt
    print("🧠 Building security analysis prompt...")
    prompt = build_security_prompt(file_contents)

    # Run analysis
    print("🤖 Querying Claude via OpenRouter for security analysis...")
    model = os.environ.get("OPENROUTER_MODEL", "meta-llama/llama-3.3-70b-instruct")
    print(f"   Model: {model}")
    result = run_claude_analysis_openrouter(prompt, openrouter_key, model)

    # Add timestamp
    from datetime import datetime
    result["scan_metadata"]["timestamp"] = datetime.utcnow().isoformat() + "Z"

    # Write report
    report_path = "claude-security-report.json"
    with open(report_path, 'w') as f:
        json.dump(result, f, indent=2)

    print(f"✅ Security report written to {report_path}")

    # Print summary
    if "summary" in result:
        summary = result["summary"]
        print("\n📊 Summary:")
        print(f"   Total issues: {summary.get('total_issues', 0)}")
        for severity in ["Critical", "High", "Medium", "Low", "Info"]:
            count = summary.get("by_severity", {}).get(severity, 0)
            if count > 0:
                print(f"   {severity}: {count}")

    # Exit with error if critical or high issues found
    critical = result.get("summary", {}).get("by_severity", {}).get("Critical", 0)
    high = result.get("summary", {}).get("by_severity", {}).get("High", 0)

    if critical > 0 or high > 0:
        print(f"\n❌ Found {critical} critical and {high} high severity issues!")
        sys.exit(1)
    else:
        print("\n✅ No critical or high severity issues found")
        sys.exit(0)


if __name__ == "__main__":
    main()
