from __future__ import annotations

import argparse
import json
import math
from dataclasses import asdict, dataclass

import networkx as nx

from .model import OptimizationState, RouteSolution
from .optimizer import DijkstraOptimizer
from .predictive import PredictiveDijkstraOptimizer
from .predictor import EdgeCostPredictor


@dataclass(frozen=True, slots=True)
class PredictiveBenchmarkResult:
    steps: int
    reactive_realized_cost: float
    predictive_realized_cost: float
    predictive_improvement_percent: float
    reactive_switches: int
    predictive_switches: int


def build_graph(step: int) -> nx.DiGraph:
    graph = nx.DiGraph()
    rising = 2.0 + 0.35 * step + 0.45 * math.sin(step / 2)
    stable = 4.6 + 0.15 * math.sin(step / 3 + 0.5)
    graph.add_edge("A", "B", cost=rising)
    graph.add_edge("B", "D", cost=rising)
    graph.add_edge("A", "C", cost=stable)
    graph.add_edge("C", "D", cost=stable)
    return graph


def realized_cost(solution: RouteSolution, graph: nx.DiGraph) -> float:
    return float(sum(graph[u][v]["cost"] for u, v in solution.edges))


def run_benchmark(steps: int = 24) -> PredictiveBenchmarkResult:
    if steps < 3:
        raise ValueError("steps must be at least 3")

    reactive_optimizer = DijkstraOptimizer()
    predictive_optimizer = PredictiveDijkstraOptimizer(
        EdgeCostPredictor(window=4, trend_damping=0.8)
    )
    reactive_cost = 0.0
    predictive_cost = 0.0
    reactive_switches = 0
    predictive_switches = 0
    previous_reactive: tuple[str, ...] | None = None
    previous_predictive: tuple[str, ...] | None = None

    for step in range(steps - 1):
        current_graph = build_graph(step)
        next_graph = build_graph(step + 1)
        current_state = OptimizationState(current_graph, "A", "D")

        predictive_optimizer.observe_state(current_state)
        reactive_solution = reactive_optimizer.solve(current_state)
        predictive_solution = predictive_optimizer.solve(current_state)

        reactive_cost += realized_cost(reactive_solution, next_graph)
        predictive_cost += realized_cost(predictive_solution, next_graph)

        if previous_reactive is not None and reactive_solution.path != previous_reactive:
            reactive_switches += 1
        if previous_predictive is not None and predictive_solution.path != previous_predictive:
            predictive_switches += 1
        previous_reactive = reactive_solution.path
        previous_predictive = predictive_solution.path

    improvement = (
        (reactive_cost - predictive_cost) / reactive_cost * 100.0 if reactive_cost else 0.0
    )
    return PredictiveBenchmarkResult(
        steps=steps,
        reactive_realized_cost=reactive_cost,
        predictive_realized_cost=predictive_cost,
        predictive_improvement_percent=improvement,
        reactive_switches=reactive_switches,
        predictive_switches=predictive_switches,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Compare reactive and predictive reoptimization")
    parser.add_argument("--steps", type=int, default=24)
    parser.add_argument("--output", type=str, default="")
    args = parser.parse_args()

    result = run_benchmark(args.steps)
    payload = json.dumps(asdict(result), indent=2, sort_keys=True)
    print(payload)
    if args.output:
        with open(args.output, "w", encoding="utf-8") as handle:
            handle.write(payload + "\n")


if __name__ == "__main__":
    main()
