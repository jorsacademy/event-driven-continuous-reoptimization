import networkx as nx
import pytest

from continuous_reoptimization import (
    DijkstraOptimizer,
    EdgeClosed,
    EdgeCostChanged,
    EdgeOpened,
    IncrementalShortestPathOptimizer,
    OptimizationState,
    ReoptimizationEngine,
)


def make_state() -> OptimizationState:
    graph = nx.DiGraph()
    graph.add_edge("A", "B", cost=4.0)
    graph.add_edge("B", "D", cost=4.0)
    graph.add_edge("A", "C", cost=5.0)
    graph.add_edge("C", "D", cost=5.0)
    graph.add_edge("B", "C", cost=1.0)
    graph.add_edge("C", "B", cost=1.0)
    return OptimizationState(graph, "A", "D")


def assert_same_solution(state: OptimizationState, incremental: IncrementalShortestPathOptimizer) -> None:
    baseline = DijkstraOptimizer().solve(state)
    repaired = incremental.solve(state)
    assert repaired.objective == pytest.approx(baseline.objective)
    assert repaired.path == baseline.path


def test_incremental_matches_dijkstra_initially() -> None:
    state = make_state()
    assert_same_solution(state, IncrementalShortestPathOptimizer())


def test_incremental_repairs_cost_increase() -> None:
    state = make_state()
    optimizer = IncrementalShortestPathOptimizer()
    optimizer.solve(state)
    state.graph["B"]["D"]["cost"] = 20.0
    state.touch()
    repaired = optimizer.solve(state)
    baseline = DijkstraOptimizer().solve(state)
    assert repaired == baseline
    assert optimizer.last_changed_edges == 1
    assert optimizer.last_expanded_vertices > 0


def test_incremental_repairs_cost_decrease() -> None:
    state = make_state()
    optimizer = IncrementalShortestPathOptimizer()
    optimizer.solve(state)
    state.graph["A"]["C"]["cost"] = 1.0
    state.touch()
    assert_same_solution(state, optimizer)
    assert optimizer.last_changed_edges == 1


def test_incremental_repairs_closure_and_reopening() -> None:
    state = make_state()
    optimizer = IncrementalShortestPathOptimizer()
    engine = ReoptimizationEngine(state, optimizer=optimizer)
    assert engine.optimize().path == ("A", "B", "D")

    closed = engine.handle(EdgeClosed(("B", "D")))
    assert closed.solution is not None
    assert closed.solution.path == DijkstraOptimizer().solve(state).path

    opened = engine.handle(EdgeOpened(("B", "D")))
    assert opened.solution is not None
    assert opened.solution.path == DijkstraOptimizer().solve(state).path


def test_engine_with_incremental_optimizer_handles_multiple_events() -> None:
    state = make_state()
    engine = ReoptimizationEngine(state, optimizer=IncrementalShortestPathOptimizer())
    engine.optimize()

    first = engine.handle(EdgeCostChanged(("B", "D"), 20.0))
    assert first.solution is not None
    assert first.solution == DijkstraOptimizer().solve(state)

    second = engine.handle(EdgeClosed(("C", "D")))
    assert second.solution is not None
    assert second.solution == DijkstraOptimizer().solve(state)

    third = engine.handle(EdgeOpened(("C", "D")))
    assert third.solution is not None
    assert third.solution == DijkstraOptimizer().solve(state)
