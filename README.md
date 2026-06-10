# TeamSmartQueue

An AI-powered ticket quality auditor. Users submit bug reports; the system audits quality, asks focused clarification questions when details are missing, rewrites complete tickets as professional bug reports, checks for duplicates, and publishes directly to GitHub Issues.

## Challenge Criteria

| Requirement | Status | Evidence |
|---|---|---|
| Guardrails | Met | Low-temperature structured Pydantic outputs, explicit anti-hallucination prompt rules, `UNKNOWN` markers for missing facts, duplicate cosine thresholding at 0.85 |
| MCP | Met | `backend/app/mcp/server.py` — FastMCP server with tools: `search_similar_tickets`, `get_ticket_template`, `create_github_issue` |
| Subagents | Met | `AuditAgent`, `QuestionAgent`, `RewriteAgent`, `SupervisorAgent` in `backend/app/agents/` |
| Context engineering | Met | Prompts pass bounded ticket context, audit findings, missing fields, and clarification answers as structured context |
| Agent memory | Met | LangGraph per-ticket/thread checkpoint memory; SQLite persists tickets, questions, findings, answers, and outputs |
| Stop hallucinations | Met | Model instructed to evaluate only explicit user text; missing rewrite sections marked `UNKNOWN`; all outputs schema-validated |
| LangChain | Met | `langchain-google-genai` / `langchain-groq` structured output in `ai_service.py` |
| LangGraph | Met | Compiled LangGraph state graph in `backend/app/agents/supervisor_agent.py` |
| LangSmith | Met when key is set | `LANGSMITH_API_KEY` in `.env`; tracing configured in `backend/app/core/tracing.py` |
| RAG / vector DB | Met | `BAAI/bge-small-en-v1.5` embeddings + persistent ChromaDB in `backend/app/services/duplicate_service.py` |
| External API | Met | GitHub REST API issue creation in `backend/app/services/github_service.py` |
| Database | Met | SQLite + SQLAlchemy async in `backend/app/database/` |
| Tests | Met | `backend/tests/` covers clarification, completed, and duplicate-stop workflow paths |

## Stack

- **Backend**: Python 3.12, FastAPI, SQLAlchemy + aiosqlite, LangChain, LangGraph, LangSmith, Gemini / Groq, ChromaDB, sentence-transformers, MCP
- **Frontend**: React + Vite, React Router
- **Integrations**: GitHub REST API, Google Gemini API, Groq API, LangSmith

## Installation & Setup

### 1. Install `uv` (Fast Python Package & Project Manager)

Install `uv` on your system using the appropriate command:

#### **Windows (PowerShell)**
```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

#### **macOS & Linux**
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

---

### 2. Set Up Virtual Environment & Dependencies

Navigate to the `backend/` directory, create a virtual environment, activate it, and install all dependencies:

#### **Windows (PowerShell)**
```powershell
cd backend
uv venv
.venv\Scripts\Activate.ps1
uv sync
```

#### **Windows (CMD)**
```cmd
cd backend
uv venv
.venv\Scripts\activate.bat
uv sync
```

#### **macOS & Linux**
```bash
cd backend
uv venv
source .venv/bin/activate
uv sync
```

---

### 3. Configure Environment Variables

Create the `.env` file from the template in the `backend/` directory and configure your keys:

```bash
cp .env.example .env
# Fill in: GEMINI_API_KEY, GITHUB_TOKEN, GITHUB_OWNER, GITHUB_REPO, LANGSMITH_API_KEY
# Optional: set GROQ_API_KEY and MODEL_PROVIDER=1 to use Groq instead of Gemini
```

---

### 4. Run the Backend Server

Start the FastAPI backend server (ensure your virtual environment is activated):

```bash
uv run uvicorn app.main:app --reload --port 8000
```
*(The SQLite database and schema migrations are auto-created on the first run).*

---

### 5. Run the Frontend App

Open a new terminal window, navigate to the `frontend/` directory, install Node dependencies, and start the React development server:

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173` in your browser, register an account, and begin submitting tickets.

## Model provider toggle

Edit `backend/.env`:

```
MODEL_PROVIDER=0   # Gemini gemini-2.5-flash (default — best quality)
MODEL_PROVIDER=1   # Groq llama-3.3-70b-versatile (faster inference)
```

When Groq is selected, OCR for image attachments still uses Gemini.

## Run tests

```bash
cd backend
uv run pytest -q
```

## Docs

| File | Contents |
|---|---|
| [docs/architecture.md](docs/architecture.md) | System diagram, layer breakdown, DB schema, status flow |
| [docs/workflow.md](docs/workflow.md) | End-to-end ticket lifecycle, agent interaction diagram |
| [docs/assumptions-limitations.md](docs/assumptions-limitations.md) | Design decisions, technical considerations |
| [docs/ai-usage-note.md](docs/ai-usage-note.md) | AI tool usage, key prompts, guardrail design |
| [docs/requirements-audit.md](docs/requirements-audit.md) | Submission checklist |
