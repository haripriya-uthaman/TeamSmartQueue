# TeamSmartQueue

### AI-Powered Developer Readiness & Ticket Intelligence Platform

TeamSmartQueue is an AI-powered ticket intelligence platform designed to improve software issue reporting and developer productivity. The system transforms incomplete bug reports into developer-ready tickets by evaluating ticket quality, identifying missing information, generating clarification questions, detecting duplicates, and automatically creating structured GitHub issues.

By ensuring tickets are complete and actionable before reaching engineering teams, TeamSmartQueue reduces triage effort, minimizes back-and-forth communication, and accelerates issue resolution.

---

## Problem Statement

Software teams frequently receive bug reports that lack critical information such as reproduction steps, environment details, expected behavior, and supporting context. This results in delayed debugging, increased communication overhead, and reduced developer efficiency.

TeamSmartQueue addresses this challenge by introducing an intelligent multi-agent workflow that improves ticket quality before assignment.

---

## Key Features

* Ticket Quality Scoring
* AI-Powered Clarification Questions
* Automatic Ticket Rewriting
* Developer Readiness Evaluation
* Duplicate Ticket Detection
* Semantic Similarity Search
* Automated GitHub Issue Creation
* Multi-Agent Ticket Processing Pipeline

---

## System Workflow

```text
User Submits Ticket
          │
          ▼
Input Guardrails
          │
          ▼
Supervisor Agent
          │
          ▼
Audit Agent
          │
          ▼
Generate Score
          │
          ▼
Missing Information?
          │
      ┌───┴────┐
      │        │
      ▼        ▼
     No       Yes
      │        │
      │        ▼
      │  Question Agent
      │        │
      │        ▼
      │  User Answers
      │        │
      │        ▼
      │   Audit Again
      │
      ▼
Rewrite Agent
      │
      ▼
Evaluation Agent
      │
      ▼
Duplicate Agent
      │
 ┌────┴────┐
 │         │
 ▼         ▼
Duplicate Unique
Found     Ticket
 │         │
 ▼         ▼
Link      MCP Tool
Ticket      │
            ▼
     GitHub Issue API
            │
            ▼
      Issue Created
```

---

## Multi-Agent Architecture

| Agent            | Responsibility                          |
| ---------------- | --------------------------------------- |
| Supervisor Agent | Controls workflow execution             |
| Audit Agent      | Evaluates ticket completeness           |
| Question Agent   | Generates clarification questions       |
| Rewrite Agent    | Converts tickets into structured format |
| Evaluation Agent | Calculates readiness score              |
| Duplicate Agent  | Detects similar historical tickets      |

---

## Technology Stack

| Component       | Technology             |
| --------------- | ---------------------- |
| Frontend        | React + Tailwind CSS   |
| Backend         | FastAPI                |
| LLM             | Gemini 2.5 Flash       |
| Embeddings      | BAAI/bge-small-en-v1.5 |
| Vector Database | ChromaDB               |
| Database        | SQLite                 |
| MCP Framework   | FastMCP                |
| API Integration | GitHub Issues API      |
| Validation      | Pydantic               |
| Logging         | Python Logging         |
| Deployment      | Localhost              |

---

## Benefits

* Improves software issue quality before assignment.
* Reduces engineering triage effort.
* Eliminates duplicate issue submissions.
* Accelerates debugging and resolution.
* Enhances communication between users and developers.
* Increases developer productivity.

---

## Future Enhancements

* Screenshot Analysis
* Browser Context Collection
* Security-Aware Issue Classification
* Jira Integration
* Slack Integration
* Advanced Analytics Dashboard
* Multi-Repository Support

---

## TeamSmartQueue

**Transforming incomplete bug reports into developer-ready issues through intelligent ticket analysis and automation.**
