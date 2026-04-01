#!/usr/bin/env python3
"""
AI PR Review - Generates an AI-powered review for a PR diff.
"""

import os
import json
import sys
from pathlib import Path

def main():
    diff_path = os.getenv('DIFF_PATH', 'pr.diff')
    pr_number = os.getenv('PR_NUMBER', '0')
    repo = os.getenv('GITHUB_REPOSITORY', '')

    # Read diff
    try:
        with open(diff_path) as f:
            diff = f.read()
    except FileNotFoundError:
        print("❌ Diff file not found")
        sys.exit(1)

    # Truncate if too large
    max_diff_size = 100000
    if len(diff) > max_diff_size:
        print(f"⚠️ Diff too large ({len(diff)} bytes), truncating to {max_diff_size}")
        diff = diff[:max_diff_size] + "\n... [truncated]"

    # Prepare prompt
    prompt = f"""You are a senior code reviewer. Review this GitHub PR diff and provide constructive feedback.

Repository: {repo}
PR Number: #{pr_number}

Focus on:
1. Code quality & best practices
2. Potential bugs or security issues
3. Missing tests or documentation
4. Suggestions for improvement
5. Overall assessment: Should merge, needs changes, or needs more review?

Be concise but thorough. Use markdown formatting.

Diff:
```diff
{diff}
```

Provide your review in this format:
## Summary
[2-3 sentence summary]

## Key Findings
- ✅ Strengths
- ⚠️ Concerns (if any)
- 🔒 Security (if relevant)

## Recommendations
- Specific, actionable suggestions

## Final Verdict
[✅ Merge / ⏳ Changes needed / ❌ Do not merge / 🤔 More review needed]"""

    # Choose API
    anthropic_key = os.getenv('ANTHROPIC_API_KEY')
    openrouter_key = os.getenv('OPENROUTER_API_KEY')
    openrouter_model = os.getenv('OPENROUTER_MODEL', 'stepfun/step-3.5-flash:free')

    review = None

    if anthropic_key:
        print("Using Anthropic API...")
        try:
            from anthropic import Anthropic
            client = Anthropic(api_key=anthropic_key)
            response = client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=2000,
                messages=[{"role": "user", "content": prompt}]
            )
            review = response.content[0].text
        except ImportError:
            print("Anthropic SDK not installed, skipping...")
            sys.exit(0)
        except Exception as e:
            print(f"Anthropic API error: {e}")
            sys.exit(0)
    elif openrouter_key:
        print("Using OpenRouter API...")
        try:
            import requests
            response = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {openrouter_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": openrouter_model,
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 2000
                },
                timeout=300
            )
            if response.status_code == 200:
                review = response.json()['choices'][0]['message']['content']
            else:
                print(f"OpenRouter error: {response.text}")
                sys.exit(0)
        except Exception as e:
            print(f"OpenRouter request failed: {e}")
            sys.exit(0)
    else:
        print("⚠️ No AI API key configured (ANTHROPIC_API_KEY or OPENROUTER_API_KEY)")
        print("AI PR review skipped. Add one of these secrets to enable.")
        sys.exit(0)

    if review is None:
        print("❌ No review generated")
        sys.exit(1)

    print("✅ AI review generated")
    print(review)

    # Save review to file
    Path("ai-pr-review.md").write_text(review)
    print("review_path=ai-pr-review.md")

    # Note: PR commenting is handled by the workflow separately if needed
    sys.exit(0)

if __name__ == "__main__":
    main()
