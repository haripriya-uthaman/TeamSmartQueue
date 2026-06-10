# Architecture

## Overview

TeamSmartQueue is a full-stack web app that turns raw user bug reports into high-quality, duplicate-free GitHub issues using an AI agent pipeline.

```
Browser (React + Vite)
        │  REST /api/v1
        ▼
FastAPI  ──►  Background Task (async, instant submit)
                    │
          ┌─────────▼──────────────────────────────────┐
          │  run_audit_and_route                        │
          │  1. OCR  (Gemini Vision, if attachments)    │
          │  2. AuditAgent  ──►  score + missing fields │
          │  3. Route:                                  │
          │     score < 70  →  needs_clarification      │
          │     score ≥ 70  →  processing pipeline      │
          └─────────────────────────────────────────────┘
                    │
          ┌─────────▼──────────────────────────────────┐
          │  SupervisorAgent  (LangGraph state graph)   │
          │  RewriteAgent   →  RewrittenTicket          │
          │  DuplicateService  →  ChromaDB cosine check │
          │  GitHubService  →  create GitHub issue      │
          └─────────────────────────────────────────────┘
                    │
             SQLite (ticket_auditor.db)
             ChromaDB (chroma_db/)
```

## Backend (`backend/`)

| Layer | Path | Responsibility |
|---|---|---|
| API routes | `app/api/v1/endpoints/` | FastAPI routers: auth, tickets, health |
| Agents | `app/agents/` | AuditAgent, QuestionAgent, RewriteAgent, SupervisorAgent |
| AI service | `app/services/ai_service.py` | Provider-agnostic wrapper — Gemini or Groq via `MODEL_PROVIDER` |
| Gemini service | `app/services/gemini_service.py` | LangChain Gemini chat model + vision OCR |
| Duplicate service | `app/services/duplicate_service.py` | ChromaDB vector search with `BAAI/bge-small-en-v1.5` embeddings |
| GitHub service | `app/services/github_service.py` | GitHub REST API issue creation via httpx |
| MCP server | `app/mcp/server.py` | FastMCP tools: similar-ticket search, ticket template, GitHub issue |
| Schemas | `app/schemas/ticket.py` | Pydantic v2 data contracts for all workflow stages |
| Database | `app/database/` | SQLAlchemy async models, session factory, auto startup migrations |
| Config | `app/core/config.py` | pydantic-settings env var loading from `.env` |
| Security | `app/core/security.py` | bcrypt password hashing, 7-day JWT auth |

## Frontend (`frontend/`)

| File | Responsibility |
|---|---|
| `src/App.jsx` | Router, auth state, theme toggle |
| `src/pages/DashboardPage.jsx` | Analytics bar, 3-column Kanban, new-ticket form, detail panel, chatbot clarification, edit mode |
| `src/pages/AllTicketsPage.jsx` | Flat searchable/filterable/sortable table |
| `src/pages/LoginPage.jsx` | Login with inline register link |
| `src/pages/RegisterPage.jsx` | Registration form |

## Database schema (SQLite)

```
users         id, email, hashed_password, created_at

tickets       id, user_id, title, description, environment,
              steps_to_reproduce, expected_result, actual_result,
              priority, severity, module_name, fix_version,
              affected_version, due_date, client, epic, sprint,
              status, score, findings, missing_information,
              ocr_text, rewritten_title, rewritten_description,
              github_issue_url, github_issue_number,
              error_message, affected_count, created_at, updated_at

questions     id, ticket_id, question_id, question_text, field_or_topic
```

## Ticket status flow

```
[submitted]
    │
    ▼ pending  (AI audit running in background)
    ├── score < 70 ──► needs_clarification  ──► (user chat answers) ──► processing
    └── score ≥ 70 ──► processing
                            │
                  duplicate?  ──yes──► duplicate_found  (original priority bumped)
                            │
                           no
                            ▼
                        completed  (GitHub issue created)

Manual:  any state  ──► closed   (Close button)
         closed/failed/duplicate  ──► pending   (Reopen button)
```

## AI provider selection

Controlled by `MODEL_PROVIDER` in `backend/.env`:

| Value | Provider | Notes |
|---|---|---|
| `0` | Google Gemini `gemini-2.5-flash` | Default. Best structured output quality. OCR included. |
| `1` | Groq `llama-3.3-70b-versatile` | Faster text inference. OCR falls back to Gemini. |
