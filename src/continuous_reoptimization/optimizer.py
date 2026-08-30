from __future__ import annotations

import heapq
import math
from collections.abc import Iterable
from typing import Protocol

import networkx as nx

from .events import Edge
from .model import OptimizationState, RouteSolution


class NoFeasibleRouteError(RuntimeError):
    pass


class Optimizer(Protocol):
    def solve(self, state: OptimizationState) -> RouteSolution: ...


class DijkstraOptimizer:
    def solve(self, state: OptimizationState) -> RouteSolution:
        graph = state.graph.copy()
        graph.remove_edges_from(state.closed_edges)
        try:
            path = nx.shortest_path(
                graph,
                state.origin,
                state.destination,
                weight="cost",
                method="dijkstra",
            )
        except (nx.NetworkXNoPath, nx.NodeNotFound) as exc:
            raise NoFeasibleRouteError("no feasible route exists") from exc

        objective = nx.path_weight(graph, path, weight="cost")
        return RouteSolution(tuple(path), float(objective))


class IncrementalShortestPathOptimizer:
    """Lifelong-planning-style shortest-path repair for fixed graph topology.

    The first call initializes shortest-path labels from the origin. Later calls compare
    effective edge costs against the previous state and repair only vertices affected by
    changed edge weights or closures. If graph topology or endpoints change, the internal
    state is rebuilt safely.
    """

    def __init__(self) -> None:
        self._origin: str | None = None
        self._destination: str | None = None
        self._nodes: frozenset[str] = frozenset()
        self._edge_costs: dict[Edge, float] = {}
        self._g: dict[str, float] = {}
        self._rhs: dict[str, float] = {}
        self._queue: list[tuple[float, float, str]] = []
        self.last_changed_edges = 0
        self.last_expanded_vertices = 0

    def solve(self, state: OptimizationState) -> RouteSolution:
        self.last_expanded_vertices = 0
        effective_costs = self._effective_costs(state)
        nodes = frozenset(str(node) for node in state.graph.nodes)

        if self._requires_reset(state, nodes, effective_costs):
            self._initialize(state, nodes, effective_costs)
        else:
            changed = [
                edge
                for edge in set(self._edge_costs) | set(effective_costs)
                if self._edge_costs.get(edge, math.inf) != effective_costs.get(edge, math.inf)
            ]
            self.last_changed_edges = len(changed)
            self._edge_costs = effective_costs
            affected = {v for _, v in changed}
            for vertex in affected:
                self._update_vertex(state, vertex)

        self._compute_shortest_path(state)
        destination = state.destination
        if math.isinf(self._g.get(destination, math.inf)):
            raise NoFeasibleRouteError("no feasible route exists")
        return self._extract_solution(state)

    def _requires_reset(
        self,
        state: OptimizationState,
        nodes: frozenset[str],
        effective_costs: dict[Edge, float],
    ) -> bool:
        if self._origin != state.origin or self._destination != state.destination:
            return True
        if self._nodes != nodes:
            return True
        if set(self._edge_costs) != set(effective_costs):
            return True
        return not self._g

    def _initialize(
        self,
        state: OptimizationState,
        nodes: frozenset[str],
        effective_costs: dict[Edge, float],
    ) -> None:
        self._origin = state.origin
        self._destination = state.destination
        self._nodes = nodes
        self._edge_costs = effective_costs
        self._g = {node: math.inf for node in nodes}
        self._rhs = {node: math.inf for node in nodes}
        if state.origin not in self._rhs or state.destination not in self._rhs:
            raise NoFeasibleRouteError("origin or destination is absent from graph")
        self._rhs[state.origin] = 0.0
        self._queue = []
        self._push(state.origin)
        self.last_changed_edges = len(effective_costs)

    def _effective_costs(self, state: OptimizationState) -> dict[Edge, float]:
        costs: dict[Edge, float] = {}
        for u, v, data in state.graph.edges(data=True):
            edge = (str(u), str(v))
            raw_cost = float(data["cost"])
            if raw_cost < 0:
                raise ValueError("edge cost must be non-negative")
            costs[edge] = math.inf if edge in state.closed_edges else raw_cost
        return costs

    def _calculate_key(self, node: str) -> tuple[float, float]:
        value = min(self._g[node], self._rhs[node])
        return (value, value)

    def _push(self, node: str) -> None:
        key = self._calculate_key(node)
        heapq.heappush(self._queue, (key[0], key[1], node))

    def _predecessors(self, state: OptimizationState, node: str) -> Iterable[str]:
        return (str(pred) for pred in state.graph.predecessors(node))

    def _successors(self, state: OptimizationState, node: str) -> Iterable[str]:
        return (str(succ) for succ in state.graph.successors(node))

    def _cost(self, u: str, v: str) -> float:
        return self._edge_costs.get((u, v), math.inf)

    def _update_vertex(self, state: OptimizationState, node: str) -> None:
        if node != state.origin:
            best = math.inf
            for pred in self._predecessors(state, node):
                best = min(best, self._g[pred] + self._cost(pred, node))
            self._rhs[node] = best
        if self._g[node] != self._rhs[node]:
            self._push(node)

    def _top_key(self) -> tuple[float, float]:
        while self._queue:
            k1, k2, node = self._queue[0]
            if (k1, k2) == self._calculate_key(node) and self._g[node] != self._rhs[node]:
                return (k1, k2)
            heapq.heappop(self._queue)
        return (math.inf, math.inf)

    def _pop_valid(self) -> str | None:
        while self._queue:
            k1, k2, node = heapq.heappop(self._queue)
            if (k1, k2) == self._calculate_key(node) and self._g[node] != self._rhs[node]:
                return node
        return None

    def _compute_shortest_path(self, state: OptimizationState) -> None:
        destination = state.destination
        while self._top_key() < self._calculate_key(destination) or self._rhs[destination] != self._g[destination]:
            node = self._pop_valid()
            if node is None:
                break
            self.last_expanded_vertices += 1
            if self._g[node] > self._rhs[node]:
                self._g[node] = self._rhs[node]
                for succ in self._successors(state, node):
                    self._update_vertex(state, succ)
            else:
                self._g[node] = math.inf
                self._update_vertex(state, node)
                for succ in self._successors(state, node):
                    self._update_vertex(state, succ)

    def _extract_solution(self, state: OptimizationState) -> RouteSolution:
        node = state.destination
        reverse_path = [node]
        seen = {node}
        while node != state.origin:
            candidates: list[tuple[float, str]] = []
            for pred in self._predecessors(state, node):
                edge_cost = self._cost(pred, node)
                score = self._g[pred] + edge_cost
                if math.isfinite(edge_cost) and math.isfinite(self._g[pred]):
                    candidates.append((score, pred))
            if not candidates:
                raise NoFeasibleRouteError("no feasible route exists")
            score, pred = min(candidates)
            if not math.isclose(score, self._g[node], rel_tol=1e-9, abs_tol=1e-9):
                raise NoFeasibleRouteError("incremental labels do not define a feasible route")
            if pred in seen:
                raise NoFeasibleRouteError("cycle encountered while extracting route")
            reverse_path.append(pred)
            seen.add(pred)
            node = pred

        path = tuple(reversed(reverse_path))
        return RouteSolution(path, float(self._g[state.destination]))
