"""Pipeline plan data models for multi-agent execution."""

from __future__ import annotations

from collections import Counter
from typing import Any

from pydantic import BaseModel, Field, model_validator

from agent_core.agents.base import AgentResult
from agent_core.agents.quality_agent import QualityReport


class PipelineNode(BaseModel):
    """One node in a pipeline, corresponding to a single workflow execution."""

    node_id: str
    workflow: str
    # Static parameters supplied directly by the user/planner.
    static_params: dict[str, Any] = Field(default_factory=dict)
    # Bindings from upstream nodes: {"param_name": "$node_id.field.path"}
    input_bindings: dict[str, str] = Field(default_factory=dict)
    # Alias for downstream references; defaults to node_id if omitted.
    output_alias: str = ""
    # Whether this node failing should abort the entire pipeline.
    critical: bool = True

    @model_validator(mode="after")
    def _set_default_alias(self) -> "PipelineNode":
        if not self.output_alias:
            self.output_alias = self.node_id
        return self


class PipelineEdge(BaseModel):
    """Execution dependency: source must complete before target can run."""

    source: str
    target: str


class PipelinePlan(BaseModel):
    """Unified execution plan for single- or multi-workflow runs."""

    plan_id: str
    nodes: list[PipelineNode]
    edges: list[PipelineEdge]

    @model_validator(mode="after")
    def _validate_references(self) -> "PipelinePlan":
        dupes = [nid for nid, cnt in Counter(n.node_id for n in self.nodes).items() if cnt > 1]
        if dupes:
            raise ValueError(f"Duplicate node_id(s): {sorted(dupes)}")

        node_ids = {n.node_id for n in self.nodes}
        aliases = {n.output_alias for n in self.nodes if n.output_alias}
        # node_ids and aliases may overlap; downstream references can use either.
        available = node_ids | aliases
        alias_to_node_id = {
            n.output_alias: n.node_id
            for n in self.nodes
            if n.output_alias and n.output_alias != n.node_id
        }

        duplicate_aliases = [
            alias
            for alias, count in Counter(n.output_alias for n in self.nodes if n.output_alias).items()
            if count > 1
        ]
        if duplicate_aliases:
            raise ValueError(
                f"Duplicate output_alias(s): {sorted(duplicate_aliases)}"
            )

        for edge in self.edges:
            # Edges express execution dependencies and must reference node_ids
            # directly. Aliases are only for input_bindings readability.
            if edge.source not in node_ids:
                raise ValueError(
                    f"Edge references unknown source node_id: {edge.source}"
                )
            if edge.target not in node_ids:
                raise ValueError(
                    f"Edge references unknown target node_id: {edge.target}"
                )
            if edge.source == edge.target:
                raise ValueError(f"Self-loop edge is not allowed: {edge.source}")

        # Validate input_bindings reference upstream nodes/aliases that are
        # topologically ordered before this node via explicit edges.
        binding_prefixes: set[str] = set()
        for node in self.nodes:
            for binding in node.input_bindings.values():
                if not binding.startswith("$"):
                    continue
                # Format: $node_id_or_alias.field.path or $node_id_or_alias[idx]
                body = binding[1:]
                prefix = body.split(".", 1)[0].split("[", 1)[0]
                binding_prefixes.add(prefix)

                ref_node_id = alias_to_node_id.get(prefix, prefix)
                if ref_node_id not in node_ids:
                    # Unknown references are reported below as a group.
                    continue
                if ref_node_id == node.node_id:
                    raise ValueError(
                        f"input_bindings cannot reference the current node: {binding}"
                    )

        unknown = binding_prefixes - available
        if unknown:
            raise ValueError(
                f"input_bindings reference unknown node/alias: {sorted(unknown)}"
            )

        # Compute transitive ancestors for every node and verify bindings only
        # reference upstream nodes/aliases.
        direct_preds: dict[str, set[str]] = {n: set() for n in node_ids}
        for edge in self.edges:
            direct_preds[edge.target].add(edge.source)

        ancestors: dict[str, set[str]] = {n: set() for n in node_ids}
        for node_id in node_ids:
            stack = list(direct_preds[node_id])
            while stack:
                pred = stack.pop()
                if pred in ancestors[node_id]:
                    continue
                ancestors[node_id].add(pred)
                stack.extend(direct_preds[pred])

        for node in self.nodes:
            for binding in node.input_bindings.values():
                if not binding.startswith("$"):
                    continue
                body = binding[1:]
                prefix = body.split(".", 1)[0].split("[", 1)[0]
                ref_node_id = alias_to_node_id.get(prefix, prefix)
                if ref_node_id not in node_ids:
                    continue
                if ref_node_id not in ancestors[node.node_id]:
                    raise ValueError(
                        f"input_bindings reference '{prefix}' is not an upstream "
                        f"node/alias of {node.node_id}: {binding}"
                    )

        self._validate_no_cycles()
        return self

    def _validate_no_cycles(self) -> None:
        """Raise ValueError if the dependency graph contains a cycle."""
        graph: dict[str, list[str]] = {n.node_id: [] for n in self.nodes}
        for edge in self.edges:
            graph[edge.source].append(edge.target)

        WHITE, GRAY, BLACK = 0, 1, 2
        color: dict[str, int] = {n: WHITE for n in graph}

        def dfs(node_id: str) -> None:
            color[node_id] = GRAY
            for neighbor in graph[node_id]:
                if color[neighbor] == GRAY:
                    raise ValueError(
                        f"PipelinePlan contains a cycle involving {node_id} -> {neighbor}"
                    )
                if color[neighbor] == WHITE:
                    dfs(neighbor)
            color[node_id] = BLACK

        for node_id in sorted(graph):
            if color[node_id] == WHITE:
                dfs(node_id)

    def get_node(self, node_id: str) -> PipelineNode:
        for node in self.nodes:
            if node.node_id == node_id:
                return node
        raise KeyError(f"Node {node_id} not found in plan")

    def topological_order(self) -> list[str]:
        """Return node_ids in dependency order.

        Uses Kahn's algorithm. Nodes with no dependencies come first.
        Raises ValueError if a cycle is detected.
        """
        graph: dict[str, set[str]] = {n.node_id: set() for n in self.nodes}
        reverse: dict[str, set[str]] = {n.node_id: set() for n in self.nodes}

        for edge in self.edges:
            graph[edge.source].add(edge.target)
            reverse[edge.target].add(edge.source)

        in_degree = {n: len(reverse[n]) for n in graph}
        queue = [n for n, d in in_degree.items() if d == 0]
        # Deterministic ordering for nodes with equal in-degree.
        queue.sort()
        order: list[str] = []

        while queue:
            node = queue.pop(0)
            order.append(node)
            for neighbor in sorted(graph[node]):
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)
                    queue.sort()

        if len(order) != len(self.nodes):
            raise ValueError("PipelinePlan contains a cycle or disconnected nodes")
        return order

    @classmethod
    def single(
        cls,
        workflow: str,
        static_params: dict[str, Any],
        plan_id: str = "",
        output_alias: str = "result",
    ) -> "PipelinePlan":
        """Convenience constructor for a single-workflow pipeline."""
        plan_id = plan_id or f"single_{workflow}"
        return cls(
            plan_id=plan_id,
            nodes=[
                PipelineNode(
                    node_id="n1",
                    workflow=workflow,
                    static_params=static_params,
                    output_alias=output_alias,
                )
            ],
            edges=[],
        )


class PipelineResult(BaseModel):
    """Result of executing a PipelinePlan."""

    plan_id: str
    success: bool
    node_results: dict[str, AgentResult] = Field(default_factory=dict)
    quality_reports: dict[str, QualityReport] = Field(default_factory=dict)
    final_report: str = ""
    errors: list[str] = Field(default_factory=list)
