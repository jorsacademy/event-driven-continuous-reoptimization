from continuous_reoptimization.predictive_benchmark import run_benchmark


def test_predictive_benchmark_reduces_next_step_realized_cost() -> None:
    result = run_benchmark(steps=24)
    assert result.predictive_realized_cost <= result.reactive_realized_cost
    assert result.predictive_improvement_percent >= 0.0
