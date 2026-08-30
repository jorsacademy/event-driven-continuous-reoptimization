import networkx as nx
import pytest

from continuous_reoptimization import (
    EdgeClosed,
    EdgeCostChanged,
    EdgeOpened,
    ManualReoptimize,
    OptimizationState,
    ReoptimizationEngine,
    TimerExpired,
    TriggerPolicy,
)


def make_engine() -> ReoptimizationEngine:
    graph = nx.DiGraph()
    graph.add_edge("A", "B", cost=4.0)
    graph.add_edge("B", "D", cost=4.0)
    graph.add_edge("A", "C", cost=5.0)
    graph.add_edge("C", "D", cost=5.0)
    graph.add_edge("X", "Y", cost=1.0)
    return ReoptimizationEngine(
        OptimizationState(graph, "A", "D"),
        policy=TriggerPolicy(max_solution_age_seconds=60),
    )


def test_initial_solution_is_optimal() -> None:
    engine = make_engine()
    solution = engine.optimize()
    assert solution.path == ("A", "B", "D")
    assert solution.objective == pytest.approx(8.0)


def test_active_edge_cost_spike_reoptimizes() -> None:
    engine = make_engine()
    engine.optimize()
    result = engine.handle(EdgeCostChanged(("B", "D"), 20.0))
    assert result.reoptimized is True
    assert result.solution is not None
    assert result.solution.path == ("A", "C", "D")
    assert result.solution.objective == pytest.approx(10.0)


def test_irrelevant_edge_change_does_not_reoptimize() -> None:
    engine = make_engine()
    first = engine.optimize()
    result = engine.handle(EdgeCostChanged(("X", "Y"), 9.0))
    assert result.reoptimized is False
    assert result.solution == first
    assert engine.solve_count == 1


def test_active_edge_closure_forces_new_route() -> None:
    engine = make_engine()
    engine.optimize()
    result = engine.handle(EdgeClosed(("B", "D")))
    assert result.solution is not None
    assert ("B", "D") not in result.solution.edges
    assert result.solution.path == ("A", "C", "D")


def test_no_route_never_keeps_stale_infeasible_solution() -> None:
    engine = make_engine()
    engine.optimize()
    engine.handle(EdgeClosed(("B", "D")))
    result = engine.handle(EdgeClosed(("C", "D")))
    assert result.reoptimized is True
    assert result.accepted is False
    assert result.solution is None
    assert engine.current_solution is None


def test_reopening_edge_triggers_reoptimization() -> None:
    engine = make_engine()
    engine.optimize()
    engine.handle(EdgeClosed(("B", "D")))
    result = engine.handle(EdgeOpened(("B", "D")))
    assert result.solution is not None
    assert result.solution.path == ("A", "B", "D")


def test_manual_refresh_always_reoptimizes() -> None:
    engine = make_engine()
    engine.optimize()
    result = engine.handle(ManualReoptimize())
    assert result.reoptimized is True
    assert engine.solve_count == 2


def test_timer_only_reoptimizes_after_threshold() -> None:
    engine = make_engine()
    engine.optimize()
    assert engine.handle(TimerExpired(30)).reoptimized is False
    assert engine.handle(TimerExpired(60)).reoptimized is True


def test_negative_cost_is_rejected() -> None:
    engine = make_engine()
    engine.optimize()
    with pytest.raises(ValueError, match="non-negative"):
        engine.handle(EdgeCostChanged(("B", "D"), -1))
