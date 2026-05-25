import app.graph.dialogue_workflow as dialogue_workflow
import app.graph.operations_workflow as operations_workflow
import app.graph.workflow as workflow
from app.graph.session import clear_sessions
from app.graph.state import create_initial_state
from app.graph.workflow import run_workflow
from app.rag.vector_store import RetrievedDocument
from app.schemas.diagnosis import DiagnosisRequest


def test_workflow_operations_route_runs_plan_execute_replan(monkeypatch) -> None:
    monkeypatch.setattr(operations_workflow, "execute_retrieval", fake_execute_retrieval)

    response = run_workflow(
        DiagnosisRequest(
            service="checkout",
            description="timeout errors",
            logs="ERROR timeout from gateway",
        )
    )

    assert response.route == "operations"
    assert response.session_id
    assert response.root_causes == ["Possible issue related to retrieved operational evidence."]
    assert response.evidence
    assert response.evidence_items[0].source == "data/docs/sample.md"
    assert response.evidence_items[0].chunk_index == 2
    assert response.evidence_items[0].retrieval_method == "hybrid_rrf"
    assert response.log_findings == ["Log contains error indicators.", "Log contains timeout indicators."]
    assert [step.action for step in response.agent_steps if step.agent == "operations"][:3] == [
        "plan",
        "intent",
        "evaluate",
    ]
    assert any(step.action == "synthesize" for step in response.agent_steps)


def test_workflow_operations_fallback_replans_when_no_evidence(monkeypatch) -> None:
    monkeypatch.setattr(operations_workflow, "execute_retrieval", fake_execute_empty_retrieval)
    monkeypatch.setattr(operations_workflow, "request_replan", lambda state: ["solution"])

    response = run_workflow(DiagnosisRequest(description="checkout timeout"))

    assert response.route == "operations"
    assert response.needs_clarification is False
    assert response.root_causes == ["Insufficient evidence to infer a specific root cause."]
    assert "Fallback" in response.report
    assert any(step.action == "replan" for step in response.agent_steps)
    assert any(step.status == "needs_replan" for step in response.agent_steps)


def test_workflow_routes_short_request_to_clarification() -> None:
    response = run_workflow(DiagnosisRequest(description="help"))

    assert response.route == "clarification"
    assert response.needs_clarification is True
    assert response.clarification_question
    assert response.root_causes == []
    assert "Clarification needed" in response.report


def test_workflow_routes_greeting_to_dialogue_react() -> None:
    response = run_workflow(DiagnosisRequest(description="hello"))

    assert response.route == "dialogue"
    assert response.needs_clarification is False
    assert response.root_causes == []
    assert "operations diagnosis" in response.report
    assert [step.action for step in response.agent_steps] == ["reason", "respond", "observe", "answer"]


def test_dialogue_faq_uses_rag_without_diagnosing(monkeypatch) -> None:
    monkeypatch.setattr(dialogue_workflow, "lookup_dialogue_rag", fake_dialogue_lookup)

    response = run_workflow(DiagnosisRequest(description="Redis READONLY 是什么"))

    assert response.route == "dialogue"
    assert "concept summary" in response.report
    assert not response.root_causes
    assert any(step.action == "rag_lookup" for step in response.agent_steps)
    assert response.agent_steps[-1].sources == ["data/docs/redis_ops_diagnosis.md"]


def test_supervisor_selects_operations_for_diagnostic_question(monkeypatch) -> None:
    monkeypatch.setattr(operations_workflow, "execute_retrieval", fake_execute_retrieval)

    final_state = workflow.workflow_graph.invoke(
        create_initial_state("checkout service has timeout errors", "ERROR timeout from gateway")
    )

    assert final_state["route"] == "operations"
    assert final_state["workflow_status"] == "completed"
    assert final_state["evidence_items"]
    assert final_state["agent_steps"]
    assert final_state["final_answer"]


def test_session_id_is_created_and_history_is_reused(monkeypatch) -> None:
    clear_sessions()
    monkeypatch.setattr(operations_workflow, "execute_retrieval", fake_execute_retrieval)

    first = run_workflow(DiagnosisRequest(description="checkout timeout"))
    second = run_workflow(DiagnosisRequest(description="checkout 500 error", session_id=first.session_id))

    assert first.session_id == second.session_id
    assert len(workflow.load_session_history(first.session_id)) == 4


def fake_execute_retrieval(query: str, top_k: int = 5) -> dict:
    return {
        "evidence_items": [
            {
                "content": "Timeout evidence",
                "source": "data/docs/sample.md",
                "chunk_index": 2,
                "score": 0.91,
                "retrieval_method": "hybrid_rrf",
            }
        ],
        "retrieved_docs": ["[source: data/docs/sample.md#chunk_2 method=hybrid_rrf score=0.9100] Timeout evidence"],
    }


def fake_execute_empty_retrieval(query: str, top_k: int = 5) -> dict:
    return {"evidence_items": [], "retrieved_docs": []}


def fake_dialogue_lookup(query: str, top_k: int = 2) -> list[RetrievedDocument]:
    return [
        RetrievedDocument(
            content="Redis READONLY means writes reached a read-only replica.",
            metadata={"source": "data/docs/redis_ops_diagnosis.md", "chunk_index": 6},
            score=0.9,
        )
    ]
