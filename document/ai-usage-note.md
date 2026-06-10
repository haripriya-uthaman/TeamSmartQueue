# AI Usage Notes

AI assistant used during development: Claude (Anthropic) via Claude Code.

## Models Used at Runtime

| Model | Provider | Purpose |
|---|---|---|
| `gemini-2.5-flash` | Google Gemini | Structured ticket audit, question generation, rewrite (default) |
| `llama-3.3-70b-versatile` | Groq | Structured ticket audit, question generation, rewrite (fast alternative) |
| `gemini-2.5-flash` (vision) | Google Gemini | OCR — extract text from image attachments |
| `BAAI/bge-small-en-v1.5` | HuggingFace (local) | 384-dim embeddings for ChromaDB duplicate detection |

The active LLM provider is controlled by `MODEL_PROVIDER` in `backend/.env` (0 = Gemini, 1 = Groq).

## Agent Prompts & Guardrails

### Audit Agent (`app/agents/audit_agent.py`)

**Purpose**: Score a submitted ticket from 0–100 and identify missing information.

**Guardrails**:
- Evaluate only text explicitly provided by the user.
- Do not assume, infer, or invent environment details, steps, or behaviors.
- Check: title, description, environment, steps to reproduce, expected result, actual result.
- Return structured JSON validated against `AuditResult` (Pydantic schema).
- Set `needs_clarification=true` when important fields are missing or vague.

### Question Agent (`app/agents/question_agent.py`)

**Purpose**: Generate focused clarification questions for missing information.

**Guardrails**:
- Ask only about fields listed in `missing_information` from the audit result.
- Maximum 3 questions — prioritise the most critical missing fields.
- Questions must be specific and actionable, not generic.
- Return structured JSON validated against `ClarificationQuestion` schema.

### Rewrite Agent (`app/agents/rewrite_agent.py`)

**Purpose**: Rewrite a ticket as a professional GitHub bug report.

**Guardrails**:
- Never invent or guess facts not present in the ticket or clarification answers.
- Any missing section must be written as `UNKNOWN` — not omitted or fabricated.
- Preserve all user-provided details exactly.
- Incorporate clarification answers naturally into the rewritten body.
- Return structured JSON validated against `RewrittenTicket` schema.

## Structured Output Enforcement

All LLM calls use LangChain's `.with_structured_output(schema)` which forces the model to return JSON matching the exact Pydantic schema. This prevents free-form responses from entering the pipeline.

Temperature is set to `0.1` for audit/question/rewrite calls to minimise randomness and hallucination.

## Duplicate Detection (non-LLM)

Duplicate checking uses local sentence-transformer embeddings and ChromaDB cosine similarity — no LLM call involved. The threshold of 0.85 was chosen to minimise false positives while catching genuinely identical reports.

## Observability

All LangChain and LangGraph calls are traced to LangSmith when `LANGSMITH_API_KEY` is set in `.env`. Each ticket run creates a named trace containing the full chain of agent calls, inputs, outputs, and latencies.
