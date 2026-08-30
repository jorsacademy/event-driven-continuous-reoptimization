from __future__ import annotations

import networkx as nx

from .model import OptimizationState, RouteSolution
from .optimizer import DijkstraOptimizer
from .predictor import EdgeCostPredictor


class PredictiveDijkstraOptimizer:
    """Optimize against short-horizon predicted edge costs.

    The live state is never mutated. A projected graph is built from current
    state plus predictor estimates and then solved with the deterministic
    Dijkstra baseline.
    """

    def __init__(self, predictor: EdgeCostPredictor | None = None) -> None:
        self.predictor = predictor or EdgeCostPredictor()
        self._baseline = DijkstraOptimizer()

    def observe_state(self, state: OptimizationState) -> None:
        for u, v, data in state.graph.edges(data=True):
            self.predictor.observe((str(u), str(v)), float(data["cost"]))

    def solve(self, state: OptimizationState) -> RouteSolution:
        projected_graph = nx.DiGraph()
        projected_graph.add_nodes_from(state.graph.nodes(data=True))
        for u, v, data in state.graph.edges(data=True):
            current_cost = float(data["cost"])
            predicted_cost = self.predictor.predict((str(u), str(v)), current_cost)
            projected_data = dict(data)
            projected_data["cost"] = predicted_cost
            projected_graph.add_edge(u, v, **projected_data)

        projected_state = OptimizationState(
            graph=projected_graph,
            origin=state.origin,
            destination=state.destination,
            closed_edges=set(state.closed_edges),
            version=state.version,
        )
        return self._baseline.solve(projected_state)
