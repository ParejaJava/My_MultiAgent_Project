"""ReAct-style dialogue sub-workflow."""

from __future__ import annotations

from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph

from app.agents.dialogue import (
    agent_step,
    build_clarification_question,
    build_dialogue_response,
    build_faq_response,
    choose_dialogue_action,
    lookup_dialogue_rag,
    normalize_question,
    observe_history,
)


class DialogueState(TypedDict):
    """State for the dialogue ReAct subgraph."""

    user_question: str
    conversation_history: list[dict[str, str]]
    action: str
    observation: str
    observations: list[str]
    sources: list[str]
    final_answer: str
    final_report: str
    clarification_question: str | None
    normalized_question: str
    agent_steps: list[dict[str, Any]]


def run_dialogue_workflow(state: dict[str, Any]) -> dict[str, Any]:
    """Run the dialogue ReAct graph and return top-level workflow updates."""
    initial_state: DialogueState = {
        "user_question": str(state.get("user_question", "")),
        "conversation_history": list(state.get("conversation_history", [])),
        "action": "",
        "observation": "",
        "observations": [],
        "sources": [],
        "final_answer": "",
        "final_report": "",
        "clarification_question": None,
        "normalized_question": str(state.get("normalized_question") or state.get("user_question", "")),
        "agent_steps": [],
    }
    result = dialogue_graph.invoke(initial_state)
    return {
        "dialogue_observations": result["observations"],
        "agent_steps": result["agent_steps"],
        "final_answer": result["final_answer"],
        "final_report": result["final_report"],
        "clarification_question": result["clarification_question"],
        "normalized_question": result["normalized_question"],
        "workflow_status": "dialogue_answer",
    }


def reason_node(state: DialogueState) -> dict[str, Any]:
    """Choose a public dialogue action."""
    action = choose_dialogue_action(state["user_question"])
    return {
        "action": action,
        "agent_steps": state["agent_steps"]
        + [agent_step("dialogue", "reason", "completed", f"Selected action: {action}")],
    }


def act_node(state: DialogueState) -> dict[str, Any]:
    """Execute the selected dialogue action."""
    action = state["action"]
    if action == "rag_lookup":
        documents = lookup_dialogue_rag(state["user_question"], top_k=2)
        answer, sources = build_faq_response(state["user_question"], documents)
        return {
            "final_answer": answer,
            "final_report": answer,
            "sources": sources,
            "observation": f"Retrieved {len(documents)} FAQ context chunks.",
            "agent_steps": state["agent_steps"]
            + [agent_step("dialogue", "rag_lookup", "completed", f"Retrieved {len(documents)} chunks.", sources)],
        }
    if action == "clarify":
        question = build_clarification_question(state["user_question"])
        return {
            "clarification_question": question,
            "final_answer": question,
            "final_report": question,
            "observation": "Clarification question generated.",
            "agent_steps": state["agent_steps"]
            + [agent_step("dialogue", "clarify", "completed", "Generated clarification question.")],
        }
    if action == "normalize":
        normalized = normalize_question(state["user_question"])
        return {
            "normalized_question": normalized,
            "final_answer": normalized,
            "final_report": normalized,
            "observation": "Question normalized for downstream processing.",
            "agent_steps": state["agent_steps"]
            + [agent_step("dialogue", "normalize", "completed", "Normalized user question.")],
        }
    answer = build_dialogue_response(state["user_question"])
    return {
        "final_answer": answer,
        "final_report": answer,
        "observation": observe_history(state["conversation_history"]),
        "agent_steps": state["agent_steps"]
        + [agent_step("dialogue", "respond", "completed", "Generated lightweight dialogue response.")],
    }


def observe_node(state: DialogueState) -> dict[str, Any]:
    """Record public observations."""
    observations = state["observations"] + [state["observation"]]
    return {
        "observations": observations,
        "agent_steps": state["agent_steps"]
        + [agent_step("dialogue", "observe", "completed", state["observation"], state["sources"])],
    }


def answer_node(state: DialogueState) -> dict[str, Any]:
    """Finalize the dialogue response."""
    return {
        "final_answer": state["final_answer"],
        "final_report": state["final_report"] or state["final_answer"],
        "agent_steps": state["agent_steps"]
        + [agent_step("dialogue", "answer", "completed", "Dialogue response finalized.", state["sources"])],
    }


def build_dialogue_graph() -> Any:
    """Build the dialogue ReAct graph."""
    graph = StateGraph(DialogueState)
    graph.add_node("reason", reason_node)
    graph.add_node("act", act_node)
    graph.add_node("observe", observe_node)
    graph.add_node("answer", answer_node)
    graph.add_edge(START, "reason")
    graph.add_edge("reason", "act")
    graph.add_edge("act", "observe")
    graph.add_edge("observe", "answer")
    graph.add_edge("answer", END)
    return graph.compile()


dialogue_graph = build_dialogue_graph()
