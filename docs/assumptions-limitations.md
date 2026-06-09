# Assumptions & Limitations

## Assumptions

### Ticket quality threshold
The audit score threshold of 70/100 for routing to clarification vs. immediate processing is a design choice. It can be adjusted in the audit agent prompt or made configurable via `.env`.

### Duplicate similarity threshold
A cosine similarity of ≥ 0.85 is treated as a duplicate. This is tuned for the `BAAI/bge-small-en-v1.5` embedding model. Lower values increase false-positive duplicate detection; higher values may miss real duplicates.

### Single-user tickets
Each ticket is submitted by one authenticated user. The `affected_count` field tracks how many duplicate submissions have been made across all users, not the actual number of end users affected in production.

### GitHub repository
The GitHub integration assumes the configured `GITHUB_REPO` exists and the `GITHUB_TOKEN` has write access (`issues: write` scope). The app does not create repositories.

### Image attachments
Only image files (PNG, JPG, GIF, WebP) up to 5 MB each are accepted for OCR. PDFs, logs, and binary files are not processed.

### Clarification questions
The Question Agent is capped at 3 questions per audit. If more than 3 fields are missing, only the most important 3 are asked. Users can also edit the ticket directly instead of answering questions.

## Known Limitations

### ChromaDB cold start
On the first ticket submission after a fresh install, the `sentence-transformers` model (`BAAI/bge-small-en-v1.5`) is downloaded from HuggingFace and loaded into memory. This can take 30–60 seconds on a slow connection.

### No real-time websockets
The frontend polls the backend every 2.5 seconds for ticket status updates. This is not a true push — in production, websockets or server-sent events would reduce unnecessary requests.

### SQLite concurrency
SQLite with `aiosqlite` is suitable for single-server development and demos. Under high concurrent write load, it should be replaced with PostgreSQL.

### AI provider for OCR
When `MODEL_PROVIDER=1` (Groq), OCR/image extraction still calls Gemini because Groq's vision model support is limited. Both `GEMINI_API_KEY` and `GROQ_API_KEY` must be set when using Groq with image attachments.

### Groq structured output
Groq's `llama-3.3-70b-versatile` supports `.with_structured_output()` via LangChain but may occasionally produce less consistent JSON structure than Gemini on complex schemas. If structured output fails, fall back to `MODEL_PROVIDER=0`.

### LangSmith tracing
LangSmith traces are only visible when `LANGSMITH_API_KEY` is a valid key. Without it, the app still functions normally — tracing is silently skipped.

### No email verification
User registration does not verify email addresses. Any email format is accepted.

### Token expiry
JWTs expire after 7 days. After expiry (or after the database is wiped), the frontend automatically detects the 401 response and logs the user out.

### ChromaDB persistence
The ChromaDB vector store is persisted at `./chroma_db` relative to where uvicorn is started. If the backend is started from a different directory, a new empty store is created. Always start from `backend/`.
