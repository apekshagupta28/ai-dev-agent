# Autonomous AI Dev Agent

A LangGraph-powered agentic pipeline that autonomously reads a Jira ticket, generates Python code using an LLM, executes and self-corrects it, pushes a GitHub Pull Request, and closes the Jira issue — end to end, without human intervention.

---

## Overview

Given a Jira issue key (e.g. `SCRUM-5`), the agent executes the following pipeline:

1. Reads the Jira ticket (summary + description)
2. Generates Python code using Groq's LLaMA 3.3-70b
3. Executes the code in a sandboxed environment
4. Self-corrects if execution fails (up to 3 retry attempts)
5. Pushes the solution to GitHub as a new branch and Pull Request
6. Closes the Jira issue with a PR link comment

---

## Architecture

```
read_jira → generate_code → execute_code → push_github → close_jira → END
                                  |               ^
                             self_correct <-- (on failure)
```

Built with LangGraph `StateGraph` for stateful, conditional node execution. The agent maintains a shared `AgentState` across all nodes, enabling clean handoffs and retry logic.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Orchestration | LangGraph (StateGraph) |
| LLM | Groq API — LLaMA 3.3-70b |
| Code Execution | Python subprocess (sandboxed) |
| GitHub Integration | PyGithub (branch + PR creation) |
| Jira Integration | Atlassian Python API |
| Dashboard | Streamlit |
| Language | Python 3.10+ |

---

## Project Structure

```
ai-dev-agent/
├── main.py              # LangGraph pipeline orchestration
├── jira_reader.py       # Fetch Jira issue details
├── code_generator.py    # LLM-based code generation (Groq)
├── code_executor.py     # Execute generated code safely
├── self_corrector.py    # LLM-based error correction loop
├── github_handler.py    # GitHub repo/branch utilities
├── github_pusher.py     # Create branch and open Pull Request
├── jira_closer.py       # Transition Jira issue to Done
├── dashboard.py         # Streamlit monitoring dashboard
└── .env                 # API keys (not committed)
```

---

## Setup

### 1. Clone the repository

```bash
git clone https://github.com/apekshagupta28/ai-dev-agent.git
cd ai-dev-agent
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure environment variables

Create a `.env` file in the root directory:

```env
GROQ_API_KEY=your_groq_api_key
GITHUB_TOKEN=your_github_pat
JIRA_URL=https://your-domain.atlassian.net
JIRA_EMAIL=your_email@example.com
JIRA_API_TOKEN=your_jira_token
GITHUB_REPO=your_username/your_repo
```

### 4. Run the pipeline

```bash
python main.py SCRUM-5
```

Replace `SCRUM-5` with any valid Jira issue key.

### 5. Launch the dashboard (optional)

```bash
streamlit run dashboard.py
```

---

## Pipeline State

The agent uses a typed `AgentState` dictionary passed across all LangGraph nodes:

| Field | Description |
|---|---|
| `issue_key`, `issue_summary`, `issue_description` | Jira context |
| `generated_code`, `filename` | LLM output |
| `execution_output`, `execution_success`, `execution_error` | Runtime results |
| `correction_attempts`, `max_corrections` | Retry control |
| `branch_name`, `pr_url`, `push_success` | GitHub output |
| `jira_closed` | Final status flag |
| `logs` | Append-only pipeline audit trail |

---

## Design Notes

**LangGraph over vanilla Python** — Enables conditional branching for the retry loop and clean state management without deeply nested control flow.

**Self-correction loop** — The agent retries up to 3 times before gracefully aborting, preventing infinite loops while maximising the success rate on fixable errors.

**Modular nodes** — Each integration (Jira, LLM, GitHub) is isolated in its own module for independent testability and easy replacement.

---

## Security

All API keys are stored in `.env` and excluded via `.gitignore`. Do not commit the `.env` file.

---

## Author

**Apeksha Gupta** — AI/ML Engineer  
[GitHub](https://github.com/apekshagupta28) · [Portfolio](https://apekshagupta28.github.io)
