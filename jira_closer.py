"""
jira_closer.py
Transitions a Jira issue to 'Done' and posts a closing comment with PR details.
"""

import os
from jira import JIRA
from dotenv import load_dotenv

load_dotenv()

JIRA_URL      = os.getenv("JIRA_URL", "https://apeksha28.atlassian.net")
JIRA_EMAIL    = os.getenv("JIRA_EMAIL")
JIRA_API_TOKEN = os.getenv("JIRA_API_TOKEN")


def get_jira_client() -> JIRA:
    return JIRA(
        server=JIRA_URL,
        basic_auth=(JIRA_EMAIL, JIRA_API_TOKEN),
    )


def get_done_transition_id(jira: JIRA, issue_key: str) -> str | None:
    """Return the transition ID that leads to a 'Done / Closed / Resolved' state."""
    transitions = jira.transitions(issue_key)
    for t in transitions:
        if t["to"]["name"].lower() in ("done", "closed", "resolved"):
            return t["id"]
    return None


def close_jira_issue(
    issue_key: str,
    pr_url: str,
    branch_name: str,
    summary: str | None = None,
) -> dict:
    """
    Transition a Jira issue to Done and post a closing comment.

    Args:
        issue_key:   e.g. 'SCRUM-5'
        pr_url:      GitHub PR URL
        branch_name: e.g. 'feat/SCRUM-5-login-flow'
        summary:     Optional plain-text summary of what was implemented

    Returns:
        dict with success flag and details
    """
    jira = get_jira_client()

    # 1. Fetch issue ──────────────────────────────────────────────────────────
    try:
        issue = jira.issue(issue_key)
    except Exception as e:
        return {"success": False, "error": f"Could not fetch issue {issue_key}: {e}"}

    current_status = issue.fields.status.name
    print(f"[jira_closer] {issue_key} current status: '{current_status}'")

    # 2. Transition to Done (skip if already terminal) ────────────────────────
    if current_status.lower() not in ("done", "closed", "resolved"):
        transition_id = get_done_transition_id(jira, issue_key)
        if not transition_id:
            available = [t["to"]["name"] for t in jira.transitions(issue_key)]
            return {
                "success": False,
                "error": (
                    f"No 'Done' transition found for {issue_key}. "
                    f"Available transitions: {available}"
                ),
            }
        try:
            jira.transition_issue(issue_key, transition_id)
            print(f"[jira_closer] Transitioned {issue_key} → Done")
        except Exception as e:
            return {"success": False, "error": f"Transition failed: {e}"}
    else:
        print(f"[jira_closer] {issue_key} already terminal – skipping transition")

    # 3. Post closing comment ─────────────────────────────────────────────────
    comment_posted = False
    try:
        jira.add_comment(issue_key, _build_comment(issue_key, pr_url, branch_name, summary))
        comment_posted = True
        print(f"[jira_closer] Comment added to {issue_key}")
    except Exception as e:
        print(f"[jira_closer] Warning: could not post comment – {e}")

    return {
        "success": True,
        "issue_key": issue_key,
        "previous_status": current_status,
        "new_status": "Done",
        "pr_url": pr_url,
        "branch_name": branch_name,
        "comment_posted": comment_posted,
    }


def _build_comment(issue_key, pr_url, branch_name, summary):
    lines = [
        "✅ *Automated Resolution by AI Dev Agent*",
        "",
        f"Issue *{issue_key}* has been implemented and is ready for review.",
        "",
        f"*Branch:* `{branch_name}`",
        f"*Pull Request:* {pr_url}",
    ]
    if summary:
        lines += ["", "*Implementation Summary:*", summary]
    lines += ["", "_Posted automatically by the AI Dev Agent pipeline._"]
    return "\n".join(lines)


# ── Smoke test ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import json
    result = close_jira_issue(
        issue_key="SCRUM-5",
        pr_url="https://github.com/apekshagupta28/ai-dev-agent/pull/1",
        branch_name="feat/SCRUM-5-example",
        summary="Implemented the feature as described in acceptance criteria.",
    )
    print(json.dumps(result, indent=2))