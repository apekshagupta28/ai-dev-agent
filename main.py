"""
main.py
LangGraph-based orchestration pipeline for the Autonomous AI Dev Agent.

Graph flow:
    read_jira → generate_code → execute_code → [error? → self_correct → execute_code]
                                                → push_github → close_jira → END
"""

import json
from typing import TypedDict, Annotated
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages

# ── Local modules ─────────────────────────────────────────────────────────────
from jira_reader    import get_jira_issue
from code_generator import generate_code
from code_executor  import run_code
from self_corrector import generate_and_fix
from github_pusher  import push_to_github
from jira_closer    import close_jira_issue


# ─────────────────────────────────────────────────────────────────────────────
# Shared pipeline state
# ─────────────────────────────────────────────────────────────────────────────
class AgentState(TypedDict):
    # Input
    issue_key: str

    # Jira
    issue_summary: str
    issue_description: str

    # Code
    generated_code: str
    filename: str

    # Execution
    execution_output: str
    execution_success: bool
    execution_error: str

    # Self-correction
    correction_attempts: int
    max_corrections: int

    # GitHub
    branch_name: str
    pr_url: str
    push_success: bool

    # Jira close
    jira_closed: bool

    # Pipeline log (append-only)
    logs: Annotated[list[str], add_messages]


# ─────────────────────────────────────────────────────────────────────────────
# Node implementations
# ─────────────────────────────────────────────────────────────────────────────

def node_read_jira(state: AgentState) -> AgentState:
    issue_key = state["issue_key"]
    print(f"\n[pipeline] 📋 Reading Jira issue {issue_key} …")
    issue = get_jira_issue(issue_key)
    return {
        **state,
        "issue_summary":     issue["summary"],
        "issue_description": issue["description"],
        "logs": [f"[read_jira] Fetched: {issue['summary']}"],
    }


def node_generate_code(state: AgentState) -> AgentState:
    print("[pipeline] 🤖 Generating code …")
    code = generate_code(
        ticket_title=state["issue_summary"],
        ticket_description=state["issue_description"],
    )
    filename = f"{state['issue_key'].lower().replace('-', '_')}_solution.py"
    return {
        **state,
        "generated_code": code,
        "filename":       filename,
        "logs": [f"[generate_code] File: {filename}"],
    }


def node_execute_code(state: AgentState) -> AgentState:
    print("[pipeline] ▶️  Executing code …")
    result = run_code(code=state["generated_code"])
    success = result.get("status") == "success"
    return {
        **state,
        "execution_output":  result.get("output", ""),
        "execution_success": success,
        "execution_error":   result.get("output", "") if not success else "",
        "logs": [f"[execute_code] {'✅ passed' if success else '❌ ' + result.get('output','')}"],
    }


def node_self_correct(state: AgentState) -> AgentState:
    attempts = state.get("correction_attempts", 0) + 1
    print(f"[pipeline] 🔧 Self-correcting (attempt {attempts}) …")
    fixed_code = generate_and_fix(
        title=state["issue_summary"],
        description=state["issue_description"],
        max_retries=1,
    )
    return {
        **state,
        "generated_code":      fixed_code or state["generated_code"],
        "correction_attempts": attempts,
        "logs": [f"[self_correct] Attempt {attempts} – patch applied"],
    }


def node_push_github(state: AgentState) -> AgentState:
    print("[pipeline] 🚀 Pushing to GitHub …")
    result = push_to_github(
        ticket_id=state["issue_key"],
        ticket_title=state["issue_summary"],
        ticket_description=state["issue_description"],
        generated_code=state["generated_code"],
    )
    return {
        **state,
        "branch_name":  result.get("branch_name", ""),
        "pr_url":       result.get("pr_url", ""),
        "push_success": bool(result.get("pr_url")),
        "logs": [f"[push_github] PR: {result.get('pr_url', 'N/A')}"],
    }


def node_close_jira(state: AgentState) -> AgentState:
    print("[pipeline] 🎯 Closing Jira issue …")
    result = close_jira_issue(
        issue_key=state["issue_key"],
        pr_url=state["pr_url"],
        branch_name=state["branch_name"],
        summary=state["issue_summary"],
    )
    return {
        **state,
        "jira_closed": result.get("success", False),
        "logs": [f"[close_jira] closed={result.get('success')}"],
    }


# ─────────────────────────────────────────────────────────────────────────────
# Routing logic
# ─────────────────────────────────────────────────────────────────────────────

def route_after_execute(state: AgentState) -> str:
    if state["execution_success"]:
        return "push_github"
    attempts = state.get("correction_attempts", 0)
    max_attempts = state.get("max_corrections", 3)
    if attempts < max_attempts:
        return "self_correct"
    print(f"[pipeline] ⚠️  Max correction attempts reached ({max_attempts}). Aborting.")
    return END


# ─────────────────────────────────────────────────────────────────────────────
# Build the LangGraph
# ─────────────────────────────────────────────────────────────────────────────

def build_graph() -> StateGraph:
    graph = StateGraph(AgentState)

    graph.add_node("read_jira",     node_read_jira)
    graph.add_node("generate_code", node_generate_code)
    graph.add_node("execute_code",  node_execute_code)
    graph.add_node("self_correct",  node_self_correct)
    graph.add_node("push_github",   node_push_github)
    graph.add_node("close_jira",    node_close_jira)

    graph.set_entry_point("read_jira")

    graph.add_edge("read_jira",     "generate_code")
    graph.add_edge("generate_code", "execute_code")
    graph.add_conditional_edges(
        "execute_code",
        route_after_execute,
        {
            "self_correct": "self_correct",
            "push_github":  "push_github",
            END:            END,
        },
    )
    graph.add_edge("self_correct", "execute_code")
    graph.add_edge("push_github",  "close_jira")
    graph.add_edge("close_jira",   END)

    return graph.compile()


# ─────────────────────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────────────────────

def run_pipeline(issue_key: str, max_corrections: int = 3) -> dict:
    """Run the full pipeline for a single Jira issue and return the final state."""
    app = build_graph()
    initial_state: AgentState = {
        "issue_key":          issue_key,
        "issue_summary":      "",
        "issue_description":  "",
        "generated_code":     "",
        "filename":           "",
        "execution_output":   "",
        "execution_success":  False,
        "execution_error":    "",
        "correction_attempts": 0,
        "max_corrections":    max_corrections,
        "branch_name":        "",
        "pr_url":             "",
        "push_success":       False,
        "jira_closed":        False,
        "logs":               [],
    }
    print(f"\n{'='*60}")
    print(f"  AI Dev Agent Pipeline — {issue_key}")
    print(f"{'='*60}")
    final_state = app.invoke(initial_state)
    print(f"\n{'='*60}")
    print(f"  Pipeline complete")
    print(f"  PR:    {final_state.get('pr_url', 'N/A')}")
    print(f"  Jira:  {'closed ✅' if final_state.get('jira_closed') else 'NOT closed ❌'}")
    print(f"{'='*60}\n")
    return final_state


if __name__ == "__main__":
    import sys
    key = sys.argv[1] if len(sys.argv) > 1 else "SCRUM-5"
    final = run_pipeline(key)
    print("\n── Final State ──")
    print(json.dumps(
        {k: v for k, v in final.items() if k != "generated_code"},
        indent=2, default=str
    ))
