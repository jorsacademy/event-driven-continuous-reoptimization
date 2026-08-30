from continuous_reoptimization.benchmark import run_benchmark


def test_benchmark_has_no_objective_mismatches() -> None:
    result = run_benchmark(size=8, events=40, seed=7)
    assert result.objective_mismatches == 0
    assert result.nodes == 64
    assert result.edges > 0
    assert result.incremental_changed_edges > 0
