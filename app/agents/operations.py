"""Operations diagnosis agent steps for plan-execute-replan workflows."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from app.agents.diagnosis import infer_root_causes
from app.agents.intent import extract_intent
from app.agents.log_analysis import analyze_logs
from app.agents.solution import generate_report
from app.config import settings
from app.llm.providers import create_llm_provider
from app.rag.hybrid_retriever import retrieve_hybrid_documents
from app.rag.vector_store import RetrievedDocument
from app.schemas.diagnosis import EvidenceItem, FaultContext


DEFAULT_OPERATIONS_RAG_CONFIG = Path("configs/rag/hybrid_rrf_rerank.yaml")
DEFAULT_PLAN = ["intent", "retrieval", "log_analysis", "diagnosis", "solution"]
ALLOWED_PLAN_STEPS = set(DEFAULT_PLAN)


def build_default_plan(log_text: str = "") -> list[str]:
    """Return the default deterministic operations plan."""
    if log_text.strip():
        return list(DEFAULT_PLAN)
    return ["intent", "retrieval", "diagnosis", "solution"]


def execute_intent(user_question: str, service: str | None = None) -> dict[str, Any]:
    """Extract incident intent."""
    intent = extract_intent(user_question)
    intent_data = intent.model_dump()
    if service:
        intent_data["system"] = service
    return {"intent": intent_data}


def execute_retrieval(query: str, top_k: int = 5) -> dict[str, Any]:
    """Retrieve operational evidence."""
    documents = retrieve_operational_evidence(query, top_k=top_k)
    evidence_items = documents_to_evidence_items(documents)
    evidence_text = [format_evidence_item(item) for item in evidence_items]
    return {
        "evidence_items": [item.model_dump() for item in evidence_items],
        "retrieved_docs": evidence_text,
    }


def execute_log_analysis(log_text: str) -> dict[str, Any]:
    """Analyze deterministic log patterns."""
    return {"log_findings": analyze_logs(log_text)}


def execute_diagnosis(intent: dict[str, Any], retrieved_docs: list[str], log_findings: list[str]) -> dict[str, Any]:
    """Infer likely root causes from structured evidence."""
    context = FaultContext(
        service=intent.get("system"),
        description=intent.get("symptom") or "",
        logs="",
    )
    return {"root_causes": infer_root_causes(context, retrieved_docs + log_findings)}


def execute_solution(root_causes: list[str], retrieved_docs: list[str], log_findings: list[str]) -> dict[str, Any]:
    """Generate the final operations report."""
    report = generate_report(root_causes, retrieved_docs, log_findings)
    return {
        "solution": "Review the listed evidence and validate the likely root causes.",
        "final_report": report,
        "final_answer": report,
    }


def retrieve_operational_evidence(query: str, top_k: int = 5) -> list[RetrievedDocument]:
    """Retrieve operations knowledge using the production hybrid RAG config."""
    config_path = Path(getattr(settings, "operations_rag_config_path", DEFAULT_OPERATIONS_RAG_CONFIG))
    return retrieve_hybrid_documents(query, top_k=top_k, config_path=config_path)


def should_replan(state: dict[str, Any]) -> str | None:
    """Return a controlled reason when the operations workflow should replan."""
    completed = set(state.get("completed_steps", []))
    if "solution" in completed:
        return None
    if "retrieval" in completed and not state.get("retrieved_docs"):
        return "retrieval_returned_no_evidence"
    if "intent" in completed:
        intent = state.get("intent", {}) if isinstance(state.get("intent"), dict) else {}
        if not intent.get("system") and not intent.get("symptom"):
            return "missing_service_and_symptom"
    if "log_analysis" in completed and state.get("log_findings") and not state.get("retrieved_docs"):
        return "logs_exist_without_retrieved_evidence"
    return None


def request_replan(state: dict[str, Any]) -> list[str]:
    """Ask the configured LLM for a constrained replan and validate the result."""
    config = {
        "llm": {
            "provider": "mock",
        }
    }
    provider = create_llm_provider(config)
    prompt = (
        "Return a comma-separated subset of these allowed steps only: "
        f"{', '.join(DEFAULT_PLAN)}. "
        f"Reason: {state.get('replan_reason') or 'unknown'}."
    )
    response = provider.generate("You are a constrained operations replanner.", prompt)
    requested_steps = [
        step.strip()
        for step in response.replace("\n", ",").split(",")
        if step.strip() in ALLOWED_PLAN_STEPS
    ]
    return requested_steps or ["solution"]


def documents_to_evidence_items(documents: list[RetrievedDocument]) -> list[EvidenceItem]:
    """Convert retrieved documents into structured evidence items."""
    evidence_items: list[EvidenceItem] = []
    for document in documents:
        metadata = document.metadata
        raw_chunk_index = metadata.get("chunk_index")
        chunk_index = raw_chunk_index if isinstance(raw_chunk_index, int) else None
        if isinstance(raw_chunk_index, str) and raw_chunk_index.isdigit():
            chunk_index = int(raw_chunk_index)
        evidence_items.append(
            EvidenceItem(
                content=document.content,
                source=str(metadata.get("source", "unknown")),
                chunk_index=chunk_index,
                score=document.score,
                retrieval_method=str(metadata.get("retrieval_method")) if metadata.get("retrieval_method") else None,
            )
        )
    return evidence_items


def format_evidence_item(item: EvidenceItem) -> str:
    """Format structured evidence for deterministic downstream agents."""
    chunk = f"#chunk_{item.chunk_index}" if item.chunk_index is not None else ""
    method = f" method={item.retrieval_method}" if item.retrieval_method else ""
    score = f" score={item.score:.4f}" if item.score is not None else ""
    return f"[source: {item.source}{chunk}{method}{score}] {item.content}"


def operation_step(agent: str, action: str, status: str, observation: str = "", sources: list[str] | None = None) -> dict[str, Any]:
    """Build a public operations step summary."""
    return {
        "agent": agent,
        "action": action,
        "status": status,
        "observation": observation,
        "sources": sources or [],
    }
