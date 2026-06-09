# Requirements Audit

Date: 2026-06-09

## Technical Requirements

| Item | Status | Notes |
| --- | --- | --- |
| Guardrails | Met | Structured Pydantic outputs, low-temperature model calls, explicit anti-hallucination prompt rules, `UNKNOWN` markers for missing facts, duplicate thresholding. |
| MCP | Met | FastMCP server in `backend/app/mcp/server.py` with duplicate search, ticket template, and GitHub issue tools. |
| Subagents | Met | Audit, Question, Rewrite, and Supervisor agents are implemented. |
| Context engineering | Met | Prompts pass bounded ticket context, audit findings, missing fields, and clarification answers. |
| Agent memory | Met | LangGraph checkpoint memory is enabled per ticket/thread id; SQLite persists durable ticket/question/finding/output state. |
| Stop hallucinations | Met | The model is instructed not to invent facts; missing rewrite sections must be `UNKNOWN`; outputs are schema validated. |
| LangChain | Met | Gemini calls use `langchain-google-genai` structured output. |
| LangGraph | Met | Supervisor workflow is a compiled LangGraph state graph. |
| LangSmith | Met when configured | `.env` includes `LANGSMITH_API_KEY`; tracing setup is in `backend/app/core/tracing.py`. |
| RAG/vector DB for duplicate checking | Met | Uses local sentence-transformer embeddings and persistent ChromaDB. |
| External API integration | Met | GitHub REST API integration creates issues. |
| Database | Met | SQLite with SQLAlchemy async models. |
| Tests | Met for core workflow | `backend/tests/test_supervisor_langgraph.py` covers clarification, completed, and duplicate-stop paths. |

## Submission Deliverables

| Deliverable | Status | Notes |
| --- | --- | --- |
| Public GitHub repository | Needs final GitHub push | Code and docs are present locally; push to public repository before submission. |
| README | Met | Root README includes setup, run, test, and criteria mapping. |
| Demo video | Not in repo | Record a 5-7 minute walkthrough with Loom/OBS or equivalent. |
| AI usage note | Met | `docs/ai-usage-note.md` contains key prompts and AI usage notes. |
| Sample data folder | Met | `sample-data/sample-inputs/` and `sample-data/expected-outputs/` are present. |
| Test cases | Met for backend workflow | Run with `cd backend && uv run pytest -q`. |
| Team information | Not in repo | Add team name and team member details for final submission. |
| Resumes | Not in repo | Add each team member resume PDF if required by the submission portal. |

## Current Caveats

- LangSmith traces appear only when `LANGSMITH_API_KEY` is valid and tracing is enabled.
- GitHub issue creation requires valid `GITHUB_TOKEN`, `GITHUB_OWNER`, and `GITHUB_REPO`.
- Chroma duplicate detection needs indexed tickets before it can find real duplicates.
