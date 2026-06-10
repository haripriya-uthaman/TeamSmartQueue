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

## 5. Assumptions and Limitations

This section outlines the design assumptions and technical scalability considerations built into the system architecture.

### System Assumptions

1. **Quality Audit Threshold**: A baseline score of 70/100 determines if a ticket contains sufficient detail for automated routing. This threshold is fully adjustable in the system configuration to match team-specific quality standards.
2. **Duplicate Detection Tuning**: A cosine similarity threshold of 0.85, paired with the `BAAI/bge-small-en-v1.5` embedding model, is selected to optimize duplicate detection. This ensures a balanced identification of identical reports while avoiding false-positive matches.
3. **Submission Mapping**: The system maps duplicate submissions to a single ticket context and increments the `affected_count` metric, allowing team leads to track issue prevalence without cluttering the workflow.
4. **Integration Scope**: The GitHub integration is designed to interface with existing repositories using secure token-based authentication (`issues: write` scope), avoiding administrative repository mutations.
5. **Media Processing Scope**: Image attachments (PNG, JPG, GIF, WebP) up to 5 MB are processed using Gemini's multimodal vision features to extract log entries and error descriptions. Non-image binaries are bypassed to keep the processing path lightweight.
6. **Interaction Optimization**: Clarification questions are capped at a maximum of 3 per audit cycle to prevent user fatigue, with the option for the user to manually edit fields directly in the dashboard at any time.

### Technical Considerations & Scalability Scope

Rather than absolute limitations, the system has been architected with clear boundaries to enable zero-configuration local runs while remaining fully prepared for production scaling:

1. **Database Portability (SQLite to PostgreSQL)**:
   * **Development**: Uses SQLite with `aiosqlite` for zero-configuration, self-contained local runs.
   * **Scaling**: Built entirely with SQLAlchemy ORM, making it fully ready to migrate to a production database like PostgreSQL by simply updating the connection string in the `.env` file.
2. **Local Model Caching**:
   * **Development**: The local embedding model (`BAAI/bge-small-en-v1.5`) is automatically cached to local storage on the first ticket submission.
   * **Scaling**: Once cached, all subsequent searches run locally and offline, eliminating external API latencies.
3. **Modular Observability**:
   * **Development**: LangSmith tracing is decoupled and optional.
   * **Scaling**: The observability framework is built-in; enterprise tracking can be activated instantly by adding the corresponding API keys without modifying the code.
4. **Session Management**:
   * **Development**: Secure session authentication utilizes standard JWT tokens with a 7-day expiration.
   * **Scaling**: The token lifecycle can be adjusted or integrated into enterprise OAuth/SSO systems by updating the core security module.
5. **Storage Directory Configuration**:
   * **Development**: Vector storage paths are resolved relative to the runtime workspace directory.
   * **Scaling**: The storage path can be overridden via environment variables or volume mounts for clean containerized deployment (e.g., Docker).
