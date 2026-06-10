# Backend

FastAPI backend for TeamSmartQueue's AI ticket workflow.

## Agent Workflow

`SupervisorAgent` runs a LangGraph state graph:

1. `audit`: scores the ticket and checks required debugging sections.
2. `questions`: asks up to 3 clarification questions when required.
3. `rewrite`: rewrites the ticket with explicit `UNKNOWN` markers for missing facts.
4. `duplicate_check`: searches ChromaDB for similar tickets.
5. `github_issue`: creates a GitHub issue only when no duplicate is found.
6. `index_ticket`: stores the new issue in ChromaDB for future duplicate checks.

LangGraph checkpoint memory is keyed by ticket/thread id. SQLite stores durable ticket state, findings, questions, answers, rewritten output, and GitHub issue metadata.

## Environment

Copy `.env.example` to `.env` and fill:

- `GEMINI_API_KEY`
- `GITHUB_TOKEN`
- `GITHUB_OWNER`
- `GITHUB_REPO`
- `LANGSMITH_API_KEY`

LangSmith tracing is configured automatically when `LANGSMITH_API_KEY` is present.

## Run

```bash
uv run uvicorn app.main:app --reload --port 8000
```

## Test

```bash
uv run pytest -q
```
