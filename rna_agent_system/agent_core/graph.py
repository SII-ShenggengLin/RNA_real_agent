"""Build and compile the RNA Design LangGraph workflow."""

from langgraph.graph import END, START, StateGraph

from agent_core.graph_nodes import (
    critic_node,
    route_after_critic,
    router_node,
    tool_execution_node,
)
from agent_core.state import AgentState


def build_graph():
    """Create and compile the RNA Design StateGraph."""
    workflow = StateGraph(AgentState)

    workflow.add_node("router", router_node)
    workflow.add_node("tool_execution", tool_execution_node)
    workflow.add_node("critic", critic_node)

    workflow.add_edge(START, "router")
    workflow.add_edge("router", "tool_execution")
    workflow.add_edge("tool_execution", "critic")
    workflow.add_conditional_edges(
        "critic",
        route_after_critic,
        {
            "tool_execution": "tool_execution",
            END: END,
        },
    )

    return workflow.compile()


compiled_graph = build_graph()
