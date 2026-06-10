# TeamSmartQueue

TeamSmartQueue is a state-of-the-art, AI-powered Ticket Quality Auditor and Automation pipeline. It automatically audits raw bug submissions, extracts details from image attachments using multimodal vision, resolves missing details through a smart conversational UI, runs semantic duplicate checks using vector search, and publishes finalized reports directly to GitHub Issues.

Designed with a focus on high developer productivity and minimal ticket friction, the system utilizes a multi-agent orchestration framework (built on LangGraph) to automate the lifecycle of bug reporting from creation to tracking.

---

## 1. What is the Project?

The application provides an end-to-end intelligent queue for software development teams:
*   **AI Quality Auditing**: Rates ticket completeness and highlights missing fields (steps to reproduce, environment, priority, etc.) using a structured `AuditAgent`.
*   **Multimodal OCR Processing**: Extracts error logs, tracebacks, and configuration values from uploaded screenshots using Gemini Vision.
*   **Interactive Clarification Bot**: Undergoes a multi-turn conversation with the reporter to acquire critical missing details when an audit score falls below the target threshold.
*   **Semantic Duplicate Detection**: Employs sentence embeddings (`BAAI/bge-small-en-v1.5`) and ChromaDB vector search to find and prevent duplicate bug reports, linking them automatically.
*   **Professional Ticket Rewriter**: Standardizes complete issues into professional Markdown formats, complete with clear headings, tracebacks, and environments.
*   **Automated Tooling**: Publishes finalized, complete bug reports directly to GitHub Issues using the REST API and supports Model Context Protocol (MCP) integrations.
*   **Tech Stack**:
    *   **Backend**: Python 3.12, FastAPI, SQLAlchemy (async), LangChain, LangGraph, ChromaDB, SQLite.
    *   **Frontend**: React, Vite, React Router, Vanilla CSS with custom modern styling (supporting Dark/Light theme toggles).
    *   **Integrations**: Google Gemini API (default), Groq API (fallback provider), GitHub REST API, LangSmith.

---

## 2. Setup Instruction

### Prerequisites
*   Python 3.12+
*   Node.js 18+
*   A package manager (pip, npm)

### Step 1: Install `uv` (Fast Python Package & Project Manager)
Install `uv` on your system to manage Python virtual environments and dependencies rapidly:
*   **Windows (PowerShell)**:
    ```powershell
    powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
    ```
*   **macOS & Linux**:
    ```bash
    curl -LsSf https://astral.sh/uv/install.sh | sh
    ```

### Step 2: Initialize Backend Dependencies
1. Navigate to the `backend/` directory:
    ```bash
    cd backend
    ```
2. Create and activate a virtual environment, then synchronize dependencies:
    *   **Windows (PowerShell)**:
        ```powershell
        uv venv
        .venv\Scripts\Activate.ps1
        uv sync
        ```
    *   **macOS & Linux**:
        ```bash
        uv venv
        source .venv/bin/activate
        uv sync
        ```

### Step 3: Configure Environment Variables
In the `backend/` directory, create a `.env` file from the provided example template:
```bash
cp .env.example .env
```
Open the `.env` file and configure the following credentials:
*   `GEMINI_API_KEY`: Google AI Studio API key.
*   `GITHUB_TOKEN`: GitHub Personal Access Token (requires `repo` or `write:discussion` & `write:packages` scopes to publish issues).
*   `GITHUB_OWNER`: Your GitHub username or organization name.
*   `GITHUB_REPO`: The repository name where issues should be created.
*   `LANGSMITH_API_KEY` (Optional): Key for activating tracing/debugging pipelines.

### Step 4: Setup Frontend Dependencies
Navigate to the `frontend/` directory and install the required npm packages:
```bash
cd ../frontend
npm install
```

---

## 3. Run Instruction

### Running the Backend Server
From the `backend/` directory (ensure your virtual environment is active), start the FastAPI server:
```bash
uv run uvicorn app.main:app --reload --port 8000
```
*Note: The SQLite database and schema migrations are automatically initialized and created on the first run.*

### Running the Frontend Application
From the `frontend/` directory, start the React Vite dev server:
```bash
npm run dev
```
Open `http://localhost:5173` in your web browser to view the interface.

### Running Automated Tests
To run the test suite covering the ticket workflows:
```bash
cd backend
uv run pytest -q
```

### Model Provider Toggle
The backend allows you to toggle between Gemini and Groq for core LLM inference tasks. Adjust the environment variable in `backend/.env`:
*   `MODEL_PROVIDER=0`: Google Gemini (`gemini-2.5-flash` - recommended for maximum structured output fidelity).
*   `MODEL_PROVIDER=1`: Groq (`llama-3.3-70b-versatile` - optimized for high-speed inference).
*   *(Note: Image processing and OCR operations automatically utilize Gemini Vision regardless of this setting).*

---

## 4. Architecture Overview

TeamSmartQueue leverages a modular, event-driven design to handle ticket ingestion, background auditing, and multi-agent workflows.

```
Browser (React Dashboard)
        │  REST API
        ▼
FastAPI Backend  ──►  Background Pipeline Execution (Async)
                           │
                 ┌─────────▼────────────────────────────────────┐
                 │ 1. Multi-modal OCR (Gemini Vision)           │
                 │ 2. Quality Audit (AuditAgent)                │
                 │ 3. Score Assessment (Score >= 70 Route)      │
                 └──────────────────┬───────────────────────────┘
                                    │
                         ┌──────────┴──────────┐
                         ▼                     ▼
                  [Score < 70]           [Score >= 70]
               Needs Clarification         Processing
             (User Conversation Bot)           │
                         │                     ▼
                         │               LangGraph Pipeline
                         │               ├─ RewriteAgent
                         │               ├─ Duplicate Check (ChromaDB)
                         └───────►───────┴─ GitHub Publish
```

### Main Components & Services
*   **Orchestration**: The `SupervisorAgent` controls the transition between analysis, rewriting, and duplicate detection using a compiled LangGraph state graph (`backend/app/agents/supervisor_agent.py`).
*   **Vector Search & Indexing**: Uses local `sentence-transformers` to embed ticket text and index it in ChromaDB for sub-millisecond similarity comparison.
*   **Database Schema**: A relational schema managed via SQLAlchemy with asynchronous SQLite connections to log user metadata, ticket fields, and historical audit states.

---

## 5. Design Assumptions & Production Readiness

The system has been architected to optimize local development, ensuring zero-configuration setups while remaining fully modular for enterprise deployment.

### 1. Database Portability
*   **Current State**: Utilizes SQLite via `aiosqlite` for light, zero-configuration local runs.
*   **Production Readiness**: Developed entirely using the SQLAlchemy ORM. Migrating to PostgreSQL or MySQL requires only updating the connection string in the `.env` configuration.

### 2. High-Performance Local Embeddings
*   **Current State**: Uses `BAAI/bge-small-en-v1.5` embeddings cached locally on the first run.
*   **Production Readiness**: By conducting embeddings locally on device, external network roundtrips are eliminated, increasing query speed and keeping costs low.

### 3. Media Ingestion Strategy
*   **Current State**: Multi-modal vision supports files (PNG, JPG, WebP) up to 5MB.
*   **Production Readiness**: Bypassing non-image binaries keeps the audit pipeline lightweight and protects backend processing nodes from high memory allocations.

### 4. Interactive Guardrails
*   **Current State**: Clarification sessions are capped at 3 questions per ticket.
*   **Production Readiness**: Prevents user fatigue by ensuring a quick and deterministic feedback loop, with manual override tools available to the reporter in the dashboard interface at any stage.

### 5. Extensible Observability
*   **Current State**: LangSmith tracing is decoupled and configured natively.
*   **Production Readiness**: System tracing can be connected to enterprise dashboards without code changes by supplying the workspace API credentials.
