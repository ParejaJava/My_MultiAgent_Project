# Operations Diagnosis Copilot

A minimal Python foundation for a multi-agent operations diagnosis copilot.

## Setup

```bash
python -m venv .venv
pip install -e ".[dev]"
```

Copy `.env.example` to `.env` and fill in real values when LLM calls are implemented.

## Run

```bash
uvicorn app.main:app --reload
```

Health check:

```bash
curl http://127.0.0.1:8000/health
```

Minimal diagnosis request:

```bash
curl -X POST http://127.0.0.1:8000/diagnose \
  -H "Content-Type: application/json" \
  -d "{\"service\":\"checkout\",\"description\":\"timeout errors\",\"logs\":\"ERROR timeout\"}"
```

## Tests

```bash
pytest
```

## Structure

- `app/main.py`: FastAPI entry point.
- `app/agents/`: narrow placeholder agents.
- `app/graph/`: workflow state and orchestration.
- `app/rag/`: minimal local document retrieval.
- `app/tools/`: deterministic helpers.
- `app/schemas/`: Pydantic models.
- `tests/`: unit and workflow tests.
- `scripts/`: utility scripts.
- `data/docs/`: sample knowledge base documents.
