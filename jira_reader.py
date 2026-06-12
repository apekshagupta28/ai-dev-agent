from jira import JIRA
import os
from dotenv import load_dotenv

load_dotenv()

def get_jira_issue(issue_key: str) -> dict:
    jira = JIRA(
        server=os.getenv("JIRA_URL"),
        basic_auth=(os.getenv("JIRA_EMAIL"), os.getenv("JIRA_API_TOKEN"))
    )
    issue = jira.issue(issue_key)

    print("=" * 40)
    print(f"Ticket ID   : {issue.key}")
    print(f"Title       : {issue.fields.summary}")
    print(f"Description : {issue.fields.description}")
    print(f"Status      : {issue.fields.status.name}")
    print(f"Priority    : {issue.fields.priority.name}")
    print("=" * 40)

    return {
        "summary":     issue.fields.summary,
        "description": issue.fields.description,
        "status":      issue.fields.status.name,
        "priority":    issue.fields.priority.name,
    }

if __name__ == "__main__":
    get_jira_issue("SCRUM-5")