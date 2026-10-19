"""
ai_reviewer.py
──────────────
GitHub Actions script — fetches the PR diff, sends it to Claude,
posts the review as a PR comment, and optionally approves/requests changes.

Required env vars (set as GitHub Actions secrets):
  ANTHROPIC_API_KEY  — your Anthropic API key
  GH_TOKEN           — GitHub token (automatically provided by Actions as GITHUB_TOKEN)
  GITHUB_REPOSITORY  — owner/repo  (auto-provided by Actions)
  PR_NUMBER          — PR number   (auto-provided via github.event.number)
"""

import os
import sys
import json
import requests
import anthropic

# ── Config ────────────────────────────────────────────────────────────────────
ANTHROPIC_API_KEY  = os.environ["ANTHROPIC_API_KEY"]
GH_TOKEN           = os.environ["GH_TOKEN"]
GITHUB_REPOSITORY  = os.environ["GITHUB_REPOSITORY"]   # e.g. "swat90/oulu-restaurant-chatbot"
PR_NUMBER          = os.environ["PR_NUMBER"]

GH_API = "https://api.github.com"
HEADERS = {
    "Authorization": f"Bearer {GH_TOKEN}",
    "Accept": "application/vnd.github.v3+json",
    "X-GitHub-Api-Version": "2022-11-28",
}

# ── Fetch PR diff ─────────────────────────────────────────────────────────────
def get_pr_diff():
    url = f"{GH_API}/repos/{GITHUB_REPOSITORY}/pulls/{PR_NUMBER}"
    r = requests.get(url, headers={**HEADERS, "Accept": "application/vnd.github.v3.diff"})
    r.raise_for_status()
    return r.text

def get_pr_info():
    url = f"{GH_API}/repos/{GITHUB_REPOSITORY}/pulls/{PR_NUMBER}"
    r = requests.get(url, headers=HEADERS)
    r.raise_for_status()
    return r.json()

# ── Call Claude ───────────────────────────────────────────────────────────────
REVIEW_PROMPT = """You are a senior Python engineer doing a code review on a pull request.

Repository: {repo}
PR title: {title}
PR description: {body}

Diff:
```diff
{diff}
```

Review this PR and respond in this exact JSON format:
{{
  "verdict": "APPROVE" | "REQUEST_CHANGES" | "COMMENT",
  "summary": "One sentence summary of what this PR does",
  "issues": [
    {{"severity": "critical|warning|suggestion", "file": "...", "line": "...", "message": "..."}}
  ],
  "positives": ["..."],
  "review_body": "Full markdown review body to post on GitHub. Be concise and constructive."
}}

Rules:
- APPROVE if the diff looks correct, tests pass, no critical issues
- REQUEST_CHANGES if there are bugs, missing tests, security issues, or broken logic
- COMMENT if it's minor style/suggestion only — don't block the PR
- If diff is too large (>400 lines changed), summarise and COMMENT only
- Always be constructive and specific
"""

def review_with_claude(diff: str, pr_info: dict) -> dict:
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    # Truncate very large diffs to avoid token limits
    if len(diff) > 12000:
        diff = diff[:12000] + "\n\n... [diff truncated — too large for full review]"

    prompt = REVIEW_PROMPT.format(
        repo=GITHUB_REPOSITORY,
        title=pr_info.get("title", ""),
        body=pr_info.get("body", "") or "",
        diff=diff,
    )

    message = client.messages.create(
        model="claude-opus-4-5",
        max_tokens=4000,
        messages=[{"role": "user", "content": prompt}],
    )

    raw = message.content[0].text.strip()

    # Strip markdown code fences if Claude wrapped in ```json
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.strip()

    return json.loads(raw)

# ── Post review to GitHub ─────────────────────────────────────────────────────
def post_review(verdict: str, body: str):
    """Post a PR review (approve / request changes / comment)."""
    # Map our verdict to GitHub event type
    event_map = {
        "APPROVE":          "APPROVE",
        "REQUEST_CHANGES":  "REQUEST_CHANGES",
        "COMMENT":          "COMMENT",
    }
    event = event_map.get(verdict, "COMMENT")

    url = f"{GH_API}/repos/{GITHUB_REPOSITORY}/pulls/{PR_NUMBER}/reviews"
    payload = {"body": body, "event": event}
    r = requests.post(url, headers=HEADERS, json=payload)
    r.raise_for_status()
    print(f"✅ Review posted — verdict: {event}")
    return r.json()

def post_comment(body: str):
    """Post a plain issue comment (fallback)."""
    url = f"{GH_API}/repos/{GITHUB_REPOSITORY}/issues/{PR_NUMBER}/comments"
    r = requests.post(url, headers=HEADERS, json={"body": body})
    r.raise_for_status()

# ── Format the review body ────────────────────────────────────────────────────
def format_review_body(result: dict) -> str:
    verdict_emoji = {"APPROVE": "✅", "REQUEST_CHANGES": "❌", "COMMENT": "💬"}.get(
        result["verdict"], "💬"
    )

    lines = [
        f"## {verdict_emoji} AI Code Review — {result['verdict']}",
        f"\n> {result['summary']}\n",
        result["review_body"],
    ]

    if result.get("issues"):
        lines.append("\n### Issues found")
        for issue in result["issues"]:
            sev = {"critical": "🔴", "warning": "🟡", "suggestion": "🔵"}.get(
                issue["severity"], "⚪"
            )
            loc = f"`{issue['file']}`" + (f" line {issue['line']}" if issue.get("line") else "")
            lines.append(f"- {sev} **{issue['severity'].upper()}** {loc}: {issue['message']}")

    if result.get("positives"):
        lines.append("\n### Looks good 👍")
        for p in result["positives"]:
            lines.append(f"- {p}")

    lines.append(
        "\n---\n*🤖 Reviewed by [Claude](https://claude.ai) via AI review workflow. "
        "This is an automated review — human review is still recommended for critical changes.*"
    )

    return "\n".join(lines)

# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    print(f"🔍 Reviewing PR #{PR_NUMBER} in {GITHUB_REPOSITORY}...")

    pr_info = get_pr_info()
    print(f"   Title: {pr_info['title']}")

    diff = get_pr_diff()
    print(f"   Diff size: {len(diff)} chars")

    print("🤖 Sending to Claude for review...")
    result = review_with_claude(diff, pr_info)

    print(f"   Verdict: {result['verdict']}")
    print(f"   Issues:  {len(result.get('issues', []))}")

    body = format_review_body(result)
    post_review(result["verdict"], body)

    # Exit with non-zero if Claude requested changes — blocks merge in branch protection
    if result["verdict"] == "REQUEST_CHANGES":
        print("❌ Claude requested changes — blocking merge.")
        sys.exit(1)

    print("✅ Done.")

if __name__ == "__main__":
    main()
