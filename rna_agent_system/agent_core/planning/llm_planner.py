"""LLM-driven planner using DeepSeek (or any OpenAI-compatible model).

This module provides ``LLMPlanner``, which delegates routing and step
construction to a large language model.  The LLM receives a system prompt
listing all available capabilities and workflows, then emits a JSON plan that
is parsed into an ``ExecutionPlan``.

Note: We do **not** rely on ``with_structured_output`` / ``response_format``
because some backends (e.g. DeepSeek) do not support it.  Instead we instruct
the model to emit raw JSON inside the message content and parse it manually.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Literal, Optional

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from agent_core.llm_config import get_deepseek_llm
from agent_core.planning.base import AgentContext, ExecutionPlan, PlanStep, Planner
from agent_core.tool_specs import TOOL_SPECS

_LOGGER = logging.getLogger(__name__)


class _LLMPlanStep(BaseModel):
    """Intermediate schema for LLM JSON output."""

    step_id: str = Field(..., description="Unique step identifier, e.g. 'step_1'.")
    type: Literal["capability", "workflow"] = Field(
        ...,
        description="Whether this step invokes a single tool (capability) or a multi-step workflow.",
    )
    target: str = Field(
        ...,
        description="Name of the capability or workflow to invoke. Must exist in the available list.",
    )
    input_binding: dict[str, Any] = Field(
        default_factory=dict,
        description="Input arguments for the step. Use '$state.<key>' to reference a value from shared state.",
    )
    output_key: str = Field(
        default="",
        description="Key under which the step result is written back to shared state.",
    )
    description: str = Field(
        default="",
        description="Concise human-readable description of what this step does.",
    )


class _LLMExecutionPlan(BaseModel):
    """Top-level schema returned by the LLM."""

    reasoning: str = Field(
        ..., description="Chain-of-thought reasoning for the chosen plan."
    )
    steps: list[_LLMPlanStep] = Field(
        ..., description="Ordered list of execution steps."
    )
    max_retries: int = Field(
        default=2, description="Maximum number of retries on workflow failure."
    )
    fallback_on_error: Literal["abort", "skip", "retry_with_alternative"] = Field(
        default="retry_with_alternative"
    )


class LLMPlanner(Planner):
    """Planner backend powered by an LLM.

    The LLM receives a system prompt listing all available capabilities and
    workflows, then emits a JSON plan that is converted into an
    ``ExecutionPlan``.
    """

    def __init__(
        self,
        llm=None,
        *,
        tool_specs: Optional[dict[str, Any]] = None,
        max_context_tools: int = 20,
        include_param_schemas: bool = False,
    ) -> None:
        self.llm = llm or get_deepseek_llm()
        self.tool_specs = tool_specs or TOOL_SPECS
        self.max_context_tools = max_context_tools
        self.include_param_schemas = include_param_schemas

    # ------------------------------------------------------------------
    # Prompt construction
    # ------------------------------------------------------------------

    def _build_system_prompt(
        self, context: AgentContext, *, user_text: str = ""
    ) -> str:
        """Assemble a system prompt describing the available toolbox.

        When *user_text* is provided, capabilities are filtered by keyword
        relevance so only the top ``max_context_tools`` (~20) most relevant
        tools are shown, cutting prompt length by ~50 % versus the full list.
        Workflow parameter schemas are deferred by default; only the workflow
        name and a one-line description are included.
        """
        lines: list[str] = [
            "You are an expert RNA bioinformatics workflow planner.",
            "Your job is to convert a user request into a structured execution plan.",
            "",
            "## Rules",
            "1. Prefer *workflows* when the request matches a known domain (e.g. mRNA CDS design, siRNA design, CRISPR analysis, RNA aptamer design).",
            "2. Use *capabilities* (single tools) for atomic operations (folding, BLAST, GC content, scoring) or when no workflow covers the request.",
            "3. In ``input_binding``, use literal values when they are present in the user text. Use ``$state.<key>`` only when you expect the value to be already present in shared state.",
            "4. If the user request is ambiguous or missing critical parameters, emit an empty plan (steps=[]) and explain why in ``reasoning``.",
            "5. Respond **only** with a valid JSON object. Do not wrap it in markdown code blocks or add any extra text.",
            "6. DEFAULT PARAMETERS ARE CAREFULLY TUNED — DO NOT CHANGE THEM LIGHTLY. Follow these rules EXACTLY:",
            "   a. Only include parameters in ``input_binding`` when the user EXPLICITLY mentions them in their request, OR when the parameter has NO default (marked as '(required)').",
            "   b. If a parameter has a default value (including 'None'), DO NOT include it in ``input_binding`` unless the user specifically asks for a different value.",
            "   c. 'None' is a VALID default that means 'let the workflow auto-select'. Do NOT treat 'None' as missing or required.",
            "   d. When in doubt, OMIT the parameter. The workflow knows its defaults better than you do.",
            "   e. These defaults have been chosen by domain experts. Changing them without strong evidence often makes results WORSE, not better. Be conservative.",
            "",
        ]

        # Workflows — name + one-line description only; full schema deferred
        if context.available_workflows:
            lines.append("## Available Workflows")
            for wf in sorted(context.available_workflows):
                lines.append(f"- {wf}: multi-step domain workflow")
                if self.include_param_schemas:
                    schema = context.workflow_param_schemas.get(wf)
                    if schema:
                        lines.append(
                            "  Default parameters (ONLY override when user explicitly requests a change):"
                        )
                        for line in schema.split("\n"):
                            lines.append(f"    {line}")
                        lines.append(
                            "  → The defaults above are battle-tested. Do NOT override them unless the user's request clearly contradicts them."
                        )
            lines.append("")

        # Capabilities — filtered by keyword relevance when user_text is provided
        lines.append("## Available Capabilities (single tools)")
        available_caps = self._filter_capabilities_by_keywords(
            sorted(context.available_capabilities), user_text
        )
        if len(available_caps) > self.max_context_tools:
            _LOGGER.warning(
                "Truncating capability list from %d to %d for LLM context",
                len(available_caps),
                self.max_context_tools,
            )
            available_caps = available_caps[: self.max_context_tools]
        for cap in available_caps:
            spec = self.tool_specs.get(cap)
            if spec is None:
                lines.append(f"- {cap}")
                continue
            caps = "; ".join(spec.capabilities) or "general"
            lines.append(f"- {cap}: {caps}")

        lines.append("")
        lines.append(
            "Return your result as a single JSON object (no markdown, no extra text) with this exact structure:\n"
            "{\n"
            '  "reasoning": "string",\n'
            '  "steps": [\n'
            "    {\n"
            '      "step_id": "string",\n'
            '      "type": "capability" | "workflow",\n'
            '      "target": "string",\n'
            '      "input_binding": {},\n'
            '      "output_key": "string",\n'
            '      "description": "string"\n'
            "    }\n"
            "  ],\n"
            '  "max_retries": 2,\n'
            '  "fallback_on_error": "retry_with_alternative"\n'
            "}"
        )
        return "\n".join(lines)

    def _build_user_prompt(
        self, user_text: str, state: Optional[dict[str, Any]]
    ) -> str:
        """Build the user-facing portion of the prompt."""
        parts: list[str] = [f"User request: {user_text}"]
        if state:
            # Inject a small snapshot of shared state keys so the LLM can use $state references
            snapshot = {
                k: (
                    f"<{type(v).__name__} len={len(v)}>"
                    if isinstance(v, (list, dict, str)) and len(str(v)) > 200
                    else v
                )
                for k, v in state.items()
                if not k.startswith("_") and k not in ("messages",)
            }
            if snapshot:
                parts.append(
                    f"Current shared state snapshot: {json.dumps(snapshot, ensure_ascii=False, default=str)}"
                )
        return "\n\n".join(parts)

    # ------------------------------------------------------------------
    # Planning
    # ------------------------------------------------------------------

    def plan(self, user_text: str, context: AgentContext) -> ExecutionPlan:
        """Plan without mutable state."""
        return self._plan_impl(user_text, context, state=None)

    def plan_with_state(self, user_text: str, state: dict[str, Any]) -> ExecutionPlan:
        """Plan with access to the current shared state."""
        caps = state.get("_available_capabilities", [])
        wfs = state.get("_available_workflows", [])
        wf_schemas = state.get("_workflow_param_schemas", {})
        ctx = AgentContext(
            session_id=state.get("session_id", ""),
            available_capabilities=caps,
            available_workflows=wfs,
            workflow_param_schemas=wf_schemas,
        )
        return self._plan_impl(user_text, ctx, state=state)

    def _parse_json_from_content(self, content: str) -> dict[str, Any]:
        """Extract JSON object from LLM response content.

        Handles:
        - Empty / whitespace-only content (returns empty dict).
        - Markdown code fences (```json ... ```).
        - Explanatory text before or after the JSON object.
        """
        content = content.strip()
        if not content:
            return {}

        # Strip markdown code fences if present
        if content.startswith("```"):
            # Remove opening fence (and optional language tag)
            first_newline = content.find("\n")
            if first_newline != -1:
                content = content[first_newline + 1 :]
            if content.endswith("```"):
                content = content[:-3].strip()
            return json.loads(content)

        # Try direct parse first
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            pass

        # Fallback: extract the first top-level JSON object by brace matching
        start = content.find("{")
        if start == -1:
            raise json.JSONDecodeError("No JSON object found in content", content, 0)

        depth = 0
        in_string = False
        escape_next = False
        for i, ch in enumerate(content[start:], start=start):
            if escape_next:
                escape_next = False
                continue
            if ch == "\\":
                escape_next = True
                continue
            if ch == '"':
                in_string = not in_string
                continue
            if in_string:
                continue
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    return json.loads(content[start : i + 1])

        raise json.JSONDecodeError("Unmatched braces in JSON content", content, start)

    def _filter_capabilities_by_keywords(
        self, available_caps: list[str], user_text: str
    ) -> list[str]:
        """Rank capabilities by keyword relevance to *user_text*.

        If *user_text* is empty, returns the original list unchanged.
        Otherwise, scores each capability by how many of its name tokens and
        description words overlap with the user's request, then returns the
        list sorted by descending relevance.
        """
        if not user_text:
            return available_caps

        user_words = set(user_text.lower().split())

        def _score(cap: str) -> float:
            spec = self.tool_specs.get(cap)
            score = 0.0
            # Name-token overlap (heavily weighted — name is most informative)
            name_tokens = set(cap.lower().replace("_", " ").split())
            overlap = len(name_tokens & user_words)
            score += overlap * 3.0

            # Description overlap
            if spec is not None:
                desc = " ".join(spec.capabilities).lower()
                desc_words = set(desc.split())
                score += len(desc_words & user_words) * 1.0

                # Task-tag overlap
                tags = getattr(spec, "task_tags", [])
                if tags:
                    tag_words = set(t.lower() for t in tags)
                    score += len(tag_words & user_words) * 2.0

            # Boost for domain-specific keywords found in user text
            domain_boosts = {
                "sirna": ["sirna", "si-rna", "duplex", "evitar"],
                "sgrna": ["sgrna", "sg-rna", "crispr", "crgpt", "crisot"],
                "mrna": ["mrna", "cds", "codon", "utr", "cai", "mfe"],
                "aptamer": ["aptamer", "odesign", "proteinx", "egarps"],
                "structure": ["fold", "secondary", "tertiary", "inverse", "rnainverse"],
                "aso": ["aso", "antisense", "rnaup", "rnacofold"],
                "ires": ["ires", "ribosome"],
                "interaction": ["smiles", "ligand", "rnasmol", "gernabind"],
            }
            cap_lower = cap.lower()
            for domain, keywords in domain_boosts.items():
                if domain in cap_lower:
                    for kw in keywords:
                        if kw in user_text.lower():
                            score += 2.5
                            break

            return score

        scored = [(cap, _score(cap)) for cap in available_caps]
        scored.sort(key=lambda x: x[1], reverse=True)
        return [cap for cap, _ in scored]

    def _plan_impl(
        self,
        user_text: str,
        context: AgentContext,
        state: Optional[dict[str, Any]],
    ) -> ExecutionPlan:
        system_text = self._build_system_prompt(context, user_text=user_text)
        user_prompt = self._build_user_prompt(user_text, state)

        messages = [
            SystemMessage(content=system_text),
            HumanMessage(content=user_prompt),
        ]

        try:
            raw_response = self.llm.invoke(messages)
            raw_content = (
                raw_response.content
                if hasattr(raw_response, "content")
                else str(raw_response)
            )
            parsed = self._parse_json_from_content(raw_content)
            llm_output = _LLMExecutionPlan.model_validate(parsed)
        except Exception as exc:
            _LOGGER.warning("LLM planning failed: %s", exc)
            return ExecutionPlan(steps=[])

        steps = [
            PlanStep(
                step_id=s.step_id,
                type=s.type,
                target=s.target,
                input_binding=s.input_binding,
                output_key=s.output_key,
                description=s.description,
            )
            for s in llm_output.steps
        ]

        _LOGGER.info(
            "LLM planner produced %d steps (reasoning: %s...)",
            len(steps),
            llm_output.reasoning[:120],
        )

        return ExecutionPlan(
            steps=steps,
            max_retries=llm_output.max_retries,
            fallback_on_error=llm_output.fallback_on_error,
        )
