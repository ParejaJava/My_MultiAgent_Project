# AGENTS.md

## Project Overview

This project is a Python-based multi-agent operations diagnosis copilot.

The goal is to build a maintainable multi-agent system, not a one-file demo.

The system uses:
- Python 3.11+
- FastAPI for HTTP APIs
- LangGraph for multi-agent orchestration
- OpenAI API for LLM calls
- Chroma or FAISS for local retrieval
- pytest for testing

## Project Structure

Use the following structure:

- `app/main.py`: FastAPI application entry.
- `app/agents/`: individual agent implementations.
- `app/graph/`: LangGraph state and workflow definitions.
- `app/rag/`: document loading, splitting, embedding, vector storage, and retrieval.
- `app/tools/`: deterministic tools such as log parsing and knowledge lookup.
- `app/schemas/`: Pydantic request and response models.
- `tests/`: unit tests and workflow tests.
- `scripts/`: utility scripts such as document ingestion.
- `data/docs/`: sample knowledge base documents.

## Agent Design Rules

- Keep each agent's responsibility narrow.
- Do not put all reasoning logic into one large agent.
- The Supervisor Agent should only make routing decisions.
- The Intent Agent should extract structured fault information.
- The Retrieval Agent should only retrieve evidence from the knowledge base.
- The Log Analysis Agent should analyze log patterns.
- The Diagnosis Agent should infer possible root causes.
- The Solution Agent should generate the final troubleshooting report.

## Code Style Rules

- Use type hints for public functions.
- Use Pydantic models for structured input and output.
- Keep functions small and testable.
- Avoid hard-coded API keys, file paths, or model names.
- Read configuration from environment variables or `app/config.py`.
- Do not put business logic directly into `app/main.py`.

## RAG Rules

- Preserve source metadata when loading documents.
- Retrieval results must include source information.
- Do not let the Diagnosis Agent invent evidence not found in retrieved documents or logs.
- Add fallback behavior when retrieval returns no useful results.

## Testing Rules

- Use pytest.
- Add or update tests when changing behavior.
- At minimum, test:
  - health endpoint
  - intent extraction
  - document retrieval
  - workflow execution
  - fallback behavior

## Safety Rules

- Do not execute destructive shell commands.
- Do not delete files unless explicitly requested.
- Do not commit or push to Git automatically.
- Do not expose API keys or secrets.
- Do not write real credentials into `.env.example`.

## Codex Working Rules

When modifying this project:

1. Inspect relevant files before editing.
2. Prefer minimal, targeted changes.
3. Preserve the existing architecture.
4. Explain changed files after editing.
5. If adding dependencies, explain why.
6. If tests cannot be run, explain the reason.