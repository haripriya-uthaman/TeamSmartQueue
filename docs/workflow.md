# Workflow

## End-to-end ticket lifecycle

### 1. User submits a ticket

The user fills the New Ticket form in the dashboard (title, description, environment, steps, expected/actual behaviour, priority, severity, attachments). Clicking **Submit Ticket** sends a `POST /api/v1/tickets/submit` request.

The API saves the ticket to SQLite and immediately returns `{ status: "pending", ticket_id: N }` — no waiting. All AI work happens in a background task.

### 2. Background: OCR (optional)

If the user attached image files (screenshots, error dialogs), the `run_audit_and_route` background function passes the base64 images to `GeminiService.extract_text_from_images()`. The extracted text is appended to the ticket context before auditing.

OCR is **skipped entirely** when no attachments are provided.

### 3. Background: Audit

`AuditAgent` calls the configured AI model with the full ticket context and returns a structured `AuditResult`:

- `score` — 0–100 ticket quality score
- `findings` — list of positive observations
- `missing_information` — list of missing fields/details
- `needs_clarification` — bool

Guardrails in the prompt:
- Evaluate only explicitly provided text — never assume or infer.
- Check title, description, environment, steps to reproduce, expected result, actual result.
- Return schema-validated structured JSON.

### 4a. Route: needs clarification (score < 70)

If the audit score is below 70 or `needs_clarification` is true:

1. `QuestionAgent` generates up to 3 focused questions targeting only the fields listed in `missing_information`.
2. Questions are saved to the DB and the ticket status is set to `needs_clarification`.
3. The frontend shows a **chatbot UI** — questions appear one at a time as AI chat bubbles.
4. The user answers each question. Answers are batched and submitted via `POST /api/v1/tickets/{id}/clarify`.
5. The ticket re-enters the processing pipeline with the answers appended to context.

### 4b. Route: processing pipeline (score ≥ 70)

If the ticket is complete enough, the `SupervisorAgent` (LangGraph state graph) runs:

**Step 1 — Rewrite**
`RewriteAgent` rewrites the ticket as a professional bug report using a strict template. It never invents facts — any missing section is written as `UNKNOWN`.

**Step 2 — Duplicate check**
`DuplicateService` converts the rewritten title + description to a 384-dim embedding (`BAAI/bge-small-en-v1.5`) and searches ChromaDB using cosine similarity.

- Similarity ≥ 0.85 → `duplicate_found`. The original ticket's `affected_count` is incremented and its priority is bumped one level (Low→Medium→High→Critical).
- Similarity < 0.85 → proceed to GitHub.

**Step 3 — GitHub issue creation**
`GitHubService` calls the GitHub REST API (`POST /repos/{owner}/{repo}/issues`) with the rewritten title and body. The returned issue URL and number are saved to the ticket.

Ticket status becomes `completed`.

### 5. Frontend polling

While a ticket is in `pending` or `processing` status, the detail panel polls `GET /api/v1/tickets/{id}` every 2.5 seconds and updates the board in real time.

### 6. Manual transitions

| Button | From statuses | To status |
|---|---|---|
| Close | completed, needs_clarification | closed |
| Reopen | closed, failed, duplicate_found | pending |

Reopened tickets re-enter the full audit pipeline from the beginning.

## Agent interaction diagram

```
submit ──► run_audit_and_route (background)
                │
                ├── OCR (optional, Gemini Vision)
                │
                ▼
           AuditAgent
          score + missing
                │
       ┌────────┴────────┐
    < 70                ≥ 70
       │                 │
  QuestionAgent     SupervisorAgent (LangGraph)
  save questions          │
  status=needs_clarification  ├── RewriteAgent
       │                  │    └── RewrittenTicket
  (user answers)          │
       │             DuplicateService
       └──► pipeline      │    ├── duplicate → bump priority
                          │    └── unique → GitHubService
                          │               └── create issue
                          ▼
                      completed
```
