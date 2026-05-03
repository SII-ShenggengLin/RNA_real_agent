"""Layer 5 — AgentRunner: unified entry point for all presentation layers."""

from __future__ import annotations

from typing import Any, Iterator, Optional

from langchain_core.messages import AIMessage, HumanMessage

from agent_core.capabilities.base import build_default_capability_registry
from agent_core.planning.base import ExecutionController, Planner
from agent_core.session_memory import SessionMemory
from agent_core.state import AgentState, default_state
from agent_core.tool_executor import ToolExecutor
from agent_core.workflows import (
    FullLengthMrnaDesignWorkflow,
    MrnaCdsDesignWorkflow,
    RnaAptamerDesignWorkflow,
)


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
    session_memory:
        Optional ``SessionMemory`` for multi-turn persistence.
        When *None* (default), every call to ``.run()`` starts from a
        fresh state — the legacy single-turn behaviour.
    """

    def __init__(
        self,
        planner: Planner,
        executor: ToolExecutor,
        *,
        compiled_graph: Optional[Any] = None,
        session_memory: Optional[SessionMemory] = None,
    ):
        self.planner = planner
        self.executor = executor
        self.capability_registry = build_default_capability_registry(executor)
        self.workflow_registry: dict[str, Any] = {
            "mrna_cds_design": MrnaCdsDesignWorkflow(self.capability_registry),
            "full_length_mrna_design": FullLengthMrnaDesignWorkflow(self.capability_registry),
            "rna_aptamer_design": RnaAptamerDesignWorkflow(self.capability_registry),
        }
        self.controller = ExecutionController(
            capability_registry=self.capability_registry,
            workflow_registry=self.workflow_registry,
        )
        self._compiled_graph = compiled_graph
        self.memory = session_memory

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
        explicit_state = state is not None
        if explicit_state:
            # Backward compatibility: caller supplied an explicit state.
            state["user_text"] = user_input
            state["messages"] = state.get("messages", []) + [HumanMessage(content=user_input)]
        else:
            if self.memory is not None:
                state = self.memory.load(session_id)
            else:
                state = default_state("")
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

        def _replan(s: dict[str, Any]) -> Any:
            return self.planner.plan_with_state(user_input, s)

        result_state = self.controller.execute(plan, state, replan_fn=_replan)

        if self.memory is not None and session_id and not explicit_state:
            self.memory.save(session_id, result_state)

        return result_state

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

    def stream_chat(self, user_input: str, *, session_id: str = "") -> Iterator[Any]:
        """Yield step-by-step events from the LangGraph compiled graph.

        Returns an iterator compatible with Streamlit's ``st.empty()``
        progress display pattern.

        Falls back to ``.run()`` when no compiled graph is available.
        """
        if self._compiled_graph is not None:
            if self.memory is not None:
                state = self.memory.load(session_id)
            else:
                state = default_state("")
            state["user_text"] = user_input
            state["messages"] = state.get("messages", []) + [HumanMessage(content=user_input)]
            final_state: Optional[dict[str, Any]] = None
            for event in self._compiled_graph.stream(state):
                yield event
                for v in event.values():
                    if isinstance(v, dict) and "messages" in v:
                        final_state = v
            if final_state is not None and self.memory is not None and session_id:
                self.memory.save(session_id, final_state)
        else:
            state = self.run(user_input, session_id=session_id)
            yield {"runner": state}
