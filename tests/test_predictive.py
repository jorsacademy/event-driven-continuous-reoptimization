import networkx as nx
import pytest

from continuous_reoptimization.model import OptimizationState
from continuous_reoptimization.predictive import PredictiveDijkstraOptimizer
from continuous_reoptimization.predictor import EdgeCostPredictor


def test_predictor_uses_damped_recent_trend() -> None:
    predictor = EdgeCostPredictor(window=4, trend_damping=0.5)
    edge = ("A", "B")
    predictor.observe(edge, 10.0)
    predictor.observe(edge, 14.0)
    assert predictor.predict(edge, 14.0) == pytest.approx(16.0)


def test_predictor_falls_back_to_current_cost_without_history() -> None:
    predictor = EdgeCostPredictor()
    assert predictor.predict(("A", "B"), 7.5) == pytest.approx(7.5)


def test_predictive_optimizer_can_anticipate_rising_corridor_cost() -> None:
    graph = nx.DiGraph()
    graph.add_edge("A", "B", cost=3.0)
    graph.add_edge("B", "D", cost=3.0)
    graph.add_edge("A", "C", cost=4.0)
    graph.add_edge("C", "D", cost=4.0)
    state = OptimizationState(graph, "A", "D")

    predictor = EdgeCostPredictor(trend_damping=1.0)
    optimizer = PredictiveDijkstraOptimizer(predictor)

    predictor.observe(("A", "B"), 1.0)
    predictor.observe(("A", "B"), 3.0)
    predictor.observe(("B", "D"), 1.0)
    predictor.observe(("B", "D"), 3.0)

    solution = optimizer.solve(state)
    assert solution.path == ("A", "C", "D")


def test_predictive_solver_does_not_mutate_live_graph() -> None:
    graph = nx.DiGraph()
    graph.add_edge("A", "B", cost=2.0)
    graph.add_edge("B", "D", cost=2.0)
    graph.add_edge("A", "D", cost=10.0)
    state = OptimizationState(graph, "A", "D")
    optimizer = PredictiveDijkstraOptimizer()
    optimizer.observe_state(state)
    optimizer.solve(state)
    assert state.graph["A"]["B"]["cost"] == pytest.approx(2.0)
    assert state.graph["A"]["D"]["cost"] == pytest.approx(10.0)
