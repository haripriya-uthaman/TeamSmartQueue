# AI Usage Note: Developer-AI Collaboration Report

This document outlines the collaborative workflow between the human developer (architect and lead engineer) and AI pair-programming assistants (Claude 3.5 Sonnet / Gemini 1.5 Pro) during the design, implementation, and testing of **TeamSmartQueue**. 

Rather than relying on AI to generate the application end-to-end, the developer served as the system architect—defining the database schemas, API routes, and agentic workflows—while leveraging AI to accelerate boilerplate generation, write unit tests, design frontend layouts, and debug complex stack traces.

---

## 1. What AI Assisted With

AI was utilized as a force-multiplier for execution speed, helping with repetitive tasks and styling logic:

*   **FastAPI & Backend Boilerplate**: Accelerated the creation of standard Pydantic schemas (e.g., `TicketCreate`, `AuditResult`, `ClarificationQuestion`) and database CRUD structures.
*   **Modern React UI & Styling**: Assisted in writing raw CSS styles, implementing a cohesive dark/light mode color palette, glassmorphism card components, and smooth hover/active transitions for the ticket dashboard.
*   **Multi-Agent Orchestration Scaffolding**: Helped scaffold the basic node structure of the LangGraph state machine (`SupervisorAgent`, `RewriteAgent`, etc.), saving time on configuration wiring.
*   **Comprehensive Test Suite**: Generated boilerplate unit tests using `pytest` and `pytest-asyncio`, including mock database sessions and mock API clients for external integrations (GitHub and Gemini).

---

## 2. What AI Got Wrong & Developer Resolutions

AI suggestions frequently required human intervention due to architectural complexity, framework evolution, and runtime edge cases:

### A. Asynchronous Session Lifecycles in Background Tasks
*   **The AI Error**: The AI originally suggested executing database updates inside FastAPI background tasks using synchronous SQLAlchemy sessions or sharing a single active database connection across requests. This caused thread blocking and intermittent connection leaks.
*   **The Resolution**: The developer refactored the database lifecycle, designing an explicit async connection context manager. Every background thread utilizes a dedicated `async_sessionmaker` inside `async with` blocks, ensuring database connections are safely released back into the pool.

### B. Infinite Loops in LangGraph Routing
*   **The AI Error**: The AI suggested conditional routing logic for the LangGraph ticket flow that did not adequately handle edge states (such as failed GitHub API responses or multiple re-audits). This resulted in circular graph executions and infinite loops.
*   **The Resolution**: The developer manually rewrote the state transitions and defined a strict, linear state machine with concrete fallback nodes. A `status` check was enforced at each step to divert failed tickets into a `failed` terminal node rather than re-routing infinitely.

### C. Deprecated ChromaDB API Integrations
*   **The AI Error**: To implement semantic duplicate detection, the AI generated vector query methods utilizing deprecated ChromaDB API calls (which were obsolete as of Chroma v0.4+). This caused the backend to crash on startup.
*   **The Resolution**: The developer referenced the official ChromaDB documentation, corrected the vector store initialization, and implemented the modern `collection.query` method with a proper distance metric.

---

## 3. Best Prompts Used during Development

The following prompts yielded the highest-quality, most accurate outputs during development by providing clear context, constraints, and strict execution rules:

### System Design Prompt (FastAPI Async Database Integration)
> "Draft a clean, async FastAPI CRUD helper file for a `Ticket` model using SQLAlchemy 2.0 with type-annotated columns (`Mapped[...]`). The database session must be injected using FastAPI dependencies. Do not use sync session methods, and ensure all queries utilize `select()` statement syntax. Handle potential `None` returns and database constraints gracefully."

### Component Styling Prompt (React & CSS)
> "Create a CSS design system for a glassmorphic dashboard container. Define custom properties for background blur, subtle borders, and color tokens (HSL) that look sleek in both dark and light modes. Add a micro-animation (0.2s cubic-bezier transition) to scale up buttons and cards slightly when hovered, and dim them when pressed. Do not use Tailwind."

### Multi-Agent Integration Prompt (LangGraph State Machine)
> "Scaffold a LangGraph StateGraph that defines three nodes: `audit`, `rewrite`, and `publish`. Define a clean typed state dictionary (`TypedDict`) containing `ticket_id`, `audit_score`, and `github_url`. Provide a conditional edge from `audit` that routes to `rewrite` if score >= 70, otherwise routes to a `needs_clarification` terminal state."
