# Assumptions & Technical Considerations

This document outlines the core assumptions made during development and details the technical considerations for scaling the application.

## System Assumptions

### 1. Quality Audit Threshold
The baseline audit score of 70/100 is used to determine if a ticket has sufficient information for immediate routing. This threshold is fully adjustable in the system configuration to fit different team quality standards.

### 2. Duplicate Detection Tuning
A cosine similarity threshold of 0.85, paired with the `BAAI/bge-small-en-v1.5` embedding model, is selected to optimize duplicate detection. This ensures a balanced identification of identical reports while avoiding false-positive matches.

### 3. Submission Mapping
The system maps duplicate submissions to a single ticket context and increments the `affected_count` metric. This allows team leads to easily track issue prevalence without cluttering the workflow with redundant issues.

### 4. Integration Scope
The GitHub integration is designed to interface with existing repositories using secure token-based authentication (`issues: write` scope), avoiding administrative repository mutations.

### 5. Media Processing Scope
Image attachments (PNG, JPG, GIF, WebP) up to 5 MB are processed using Gemini's multimodal vision features to extract log entries and error descriptions. Non-image binaries (such as raw database files or archives) are bypassed to keep the processing path lightweight.

### 6. Interaction Optimization
Clarification questions are capped at a maximum of 3 per audit cycle to prevent user fatigue. The user is presented with the option to directly update the fields via the dashboard at any time.

---

## Technical Considerations & Scalability Scope

Rather than absolute limitations, the system has been architected with clear boundaries to enable zero-configuration local runs while remaining fully prepared for production scaling:V

### 1. Database Portability (SQLite to PostgreSQL)
- **Current State**: Uses SQLite with `aiosqlite` for zero-configuration, self-contained local runs.
- **Future Scope**: Built entirely with SQLAlchemy ORM, making it fully ready to migrate to a production database like PostgreSQL by simply updating the connection string in the `.env` file.

### 2. Local Model Caching
- **Current State**: The local embedding model (`BAAI/bge-small-en-v1.5`) is automatically cached to local storage on the first ticket submission.
- **Future Scope**: Once cached, all subsequent searches run locally and offline, eliminating external API latencies.

### 3. Modular Observability
- **Current State**: LangSmith tracing is decoupled and optional.
- **Future Scope**: The observability framework is built-in; enterprise tracking can be activated instantly by adding the corresponding API keys without modifying the code.

### 4. Session Management
- **Current State**: Secure session authentication utilizes standard JWT tokens with a 7-day expiration.
- **Future Scope**: The token lifecycle can be adjusted or integrated into enterprise OAuth/SSO systems by updating the core security module.

### 5. Storage Directory Configuration
- **Current State**: Vector storage paths are resolved relative to the runtime workspace directory.
- **Future Scope**: The storage path can be overridden via environment variables or volume mounts for clean containerized deployment (e.g., Docker).

