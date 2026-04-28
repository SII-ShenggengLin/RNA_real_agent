"""Layer 5 — AgentRunner: unified entry point for all presentation layers."""

from __future__ import annotations

from typing import Any, Optional

from langchain_core.messages import AIMessage, HumanMessage

from agent_core.capabilities.base import build_default_capability_registry
from agent_core.planning.base import ExecutionController, Planner
from agent_core.state import AgentState, default_state
from agent_core.tool_executor import ToolExecutor
from agent_core.workflows import MrnaCdsDesignWorkflow


class AgentRunner:
    """Unified façade used by Streamlit, FastAPI, and CLI.

    Parameters
    ----------
    planner:
        Concrete ``Planner`` backend (e.g. ``RuleBasedPlanner``).
    executor:
        ``ToolExecutor`` used to build the ``CapabilityRegistry``.
    compiled_graph:
        Optional pre-compiled LangGraph graph.  When provided,
        ``.run_chat()`` uses it for backward compatibility.
    """

    def __init__(
        self,
        planner: Planner,
        executor: ToolExecutor,
        *,
        compiled_graph: Optional[Any] = None,
    ):
        self.planner = planner
        self.executor = executor
        self.capability_registry = build_default_capability_registry(executor)
        self.workflow_registry: dict[str, Any] = {
            "mrna_cds_design": MrnaCdsDesignWorkflow(self.capability_registry),
        }
        self.controller = ExecutionController(
            capability_registry=self.capability_registry,
            workflow_registry=self.workflow_registry,
        )
        self._compiled_graph = compiled_graph

    def run(
        self,
        user_input: str,
        *,
        session_id: str = "",
        state: Optional[AgentState] = None,
    ) -> AgentState:
        """Plan → Execute → Return updated state.

        This is the **new** unified path; it does **not** require a LangGraph
        ``compiled_graph``.  If you need the legacy LangGraph path, call
        ``run_chat()`` instead.
        """
        if state is None:
            state = default_state(user_input)
        else:
            state["user_text"] = user_input
            state["messages"] = state.get("messages", []) + [HumanMessage(content=user_input)]

        # If the planner supports plan_with_state (RuleBasedPlanner does),
        # use it so that workspace file preparation happens inline.
        if hasattr(self.planner, "plan_with_state"):
            plan = self.planner.plan_with_state(user_input, state)
        else:
            from agent_core.planning.base import AgentContext
            ctx = AgentContext(session_id=session_id, available_capabilities=self.capability_registry.list_names())
            plan = self.planner.plan(user_input, ctx)

        state["_execution_plan"] = plan.model_dump(mode="json")

        # Add a routing message for observability
        route = state.get("route", "mrna")
        state["messages"] = state.get("messages", []) + [
            AIMessage(content=f"Router decision (rule-based): {route}")
        ]

        return self.controller.execute(plan, state)

    def run_chat(self, user_input: str) -> AgentState:
        """Legacy LangGraph chat path.

        Uses the pre-compiled graph (if available) for full backward
        compatibility with the existing Streamlit frontend.
        """
        if self._compiled_graph is None:
            raise RuntimeError(
                "AgentRunner was created without a compiled_graph; "
                "use .run() for the new unified path, or pass compiled_graph=..."
            )
        state = default_state(user_input)
        return self._compiled_graph.invoke(state)

    def stream_chat(self, user_input: str):
        """Yield step-by-step events from the LangGraph compiled graph.

        Returns an iterator compatible with Streamlit's ``st.empty()``
        progress display pattern.
        """
        if self._compiled_graph is None:
            raise RuntimeError(
                "AgentRunner was created without a compiled_graph; "
                "use .run() for the new unified path, or pass compiled_graph=..."
            )
        state = default_state(user_input)
        yield from self._compiled_graph.stream(state)
