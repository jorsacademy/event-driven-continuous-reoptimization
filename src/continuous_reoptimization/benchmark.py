from __future__ import annotations

import argparse
import json
import random
import time
from dataclasses import asdict, dataclass

import networkx as nx

from .model import OptimizationState
from .optimizer import DijkstraOptimizer, IncrementalShortestPathOptimizer


@dataclass(frozen=True, slots=True)
class BenchmarkResult:
    nodes: int
    edges: int
    events: int
    seed: int
    dijkstra_seconds: float
    incremental_seconds: float
    speedup: float
    objective_mismatches: int
    incremental_expanded_vertices: int
    incremental_changed_edges: int


def build_grid(size: int) -> nx.DiGraph:
    graph = nx.DiGraph()
    for row in range(size):
        for col in range(size):
            node = f"{row}:{col}"
            if col + 1 < size:
                right = f"{row}:{col + 1}"
                weight = 1.0 + ((row * 17 + col * 13) % 9) / 20.0
                graph.add_edge(node, right, cost=weight)
                graph.add_edge(right, node, cost=weight + 0.07)
            if row + 1 < size:
                down = f"{row + 1}:{col}"
                weight = 1.0 + ((row * 11 + col * 19) % 11) / 20.0
                graph.add_edge(node, down, cost=weight)
                graph.add_edge(down, node, cost=weight + 0.05)
    return graph


def generate_events(graph: nx.DiGraph, count: int, seed: int) -> list[tuple[str, str, float]]:
    rng = random.Random(seed)
    edges = sorted((str(u), str(v)) for u, v in graph.edges)
    events: list[tuple[str, str, float]] = []
    for index in range(count):
        u, v = edges[rng.randrange(len(edges))]
        base = float(graph[u][v]["cost"])
        multiplier = 0.55 + rng.random() * 2.25
        jitter = ((index % 7) - 3) * 0.01
        events.append((u, v, max(0.01, base * multiplier + jitter)))
    return events


def run_benchmark(size: int = 30, events: int = 250, seed: int = 42) -> BenchmarkResult:
    baseline_graph = build_grid(size)
    incremental_graph = baseline_graph.copy()
    event_stream = generate_events(baseline_graph, events, seed)

    origin = "0:0"
    destination = f"{size - 1}:{size - 1}"
    baseline_state = OptimizationState(baseline_graph, origin, destination)
    incremental_state = OptimizationState(incremental_graph, origin, destination)

    dijkstra = DijkstraOptimizer()
    incremental = IncrementalShortestPathOptimizer()

    start = time.perf_counter()
    baseline_initial = dijkstra.solve(baseline_state)
    dijkstra_seconds = time.perf_counter() - start

    start = time.perf_counter()
    incremental_initial = incremental.solve(incremental_state)
    incremental_seconds = time.perf_counter() - start

    mismatches = int(abs(baseline_initial.objective - incremental_initial.objective) > 1e-9)
    expanded_vertices = incremental.last_expanded_vertices
    changed_edges = incremental.last_changed_edges

    for u, v, new_cost in event_stream:
        baseline_state.graph[u][v]["cost"] = new_cost
        baseline_state.touch()
        incremental_state.graph[u][v]["cost"] = new_cost
        incremental_state.touch()

        start = time.perf_counter()
        baseline_solution = dijkstra.solve(baseline_state)
        dijkstra_seconds += time.perf_counter() - start

        start = time.perf_counter()
        incremental_solution = incremental.solve(incremental_state)
        incremental_seconds += time.perf_counter() - start

        if abs(baseline_solution.objective - incremental_solution.objective) > 1e-8:
            mismatches += 1
        expanded_vertices += incremental.last_expanded_vertices
        changed_edges += incremental.last_changed_edges

    speedup = dijkstra_seconds / incremental_seconds if incremental_seconds > 0 else float("inf")
    return BenchmarkResult(
        nodes=baseline_graph.number_of_nodes(),
        edges=baseline_graph.number_of_edges(),
        events=events,
        seed=seed,
        dijkstra_seconds=dijkstra_seconds,
        incremental_seconds=incremental_seconds,
        speedup=speedup,
        objective_mismatches=mismatches,
        incremental_expanded_vertices=expanded_vertices,
        incremental_changed_edges=changed_edges,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Compare full and incremental reoptimization")
    parser.add_argument("--size", type=int, default=30)
    parser.add_argument("--events", type=int, default=250)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--output", type=str, default="")
    args = parser.parse_args()

    result = run_benchmark(args.size, args.events, args.seed)
    payload = json.dumps(asdict(result), indent=2, sort_keys=True)
    print(payload)
    if args.output:
        with open(args.output, "w", encoding="utf-8") as handle:
            handle.write(payload + "\n")

    if result.objective_mismatches:
        raise SystemExit("incremental solver disagreed with Dijkstra baseline")


if __name__ == "__main__":
    main()
