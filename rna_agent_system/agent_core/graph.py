"""Build and compile the RNA Design LangGraph workflow."""

from langgraph.graph import END, START, StateGraph

from agent_core.nodes import (
    crispr_specialist_node,
    critic_node,
    mrna_specialist_node,
    route_after_critic,
    route_after_router,
    router_node,
    sirna_specialist_node,
    tool_execution_node,
)
from agent_core.state import AgentState


def build_graph():
    """Create and compile the RNA Design StateGraph."""
    workflow = StateGraph(AgentState)

    workflow.add_node("router", router_node)
    workflow.add_node("sirna_specialist", sirna_specialist_node)
    workflow.add_node("mrna_specialist", mrna_specialist_node)
    workflow.add_node("crispr_specialist", crispr_specialist_node)
    workflow.add_node("tool_execution", tool_execution_node)
    workflow.add_node("critic", critic_node)

    workflow.add_edge(START, "router")
    workflow.add_conditional_edges(
        "router",
        route_after_router,
        {
            "sirna_specialist": "sirna_specialist",
            "mrna_specialist": "mrna_specialist",
            "crispr_specialist": "crispr_specialist",
            "end": END,
        },
    )
    workflow.add_edge("sirna_specialist", "tool_execution")
    workflow.add_edge("mrna_specialist", "tool_execution")
    workflow.add_edge("crispr_specialist", "tool_execution")
    workflow.add_edge("tool_execution", "critic")
    workflow.add_conditional_edges(
        "critic",
        route_after_critic,
        {
            "sirna_specialist": "sirna_specialist",
            "mrna_specialist": "mrna_specialist",
            "crispr_specialist": "crispr_specialist",
            "end": END,
        },
    )

    return workflow.compile()


compiled_graph = build_graph()
