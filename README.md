# Event-Driven Continuous Reoptimization

A compact research and engineering project for optimization systems that react to changing state, constraints, and operating conditions.

The core idea is simple: maintain a current feasible solution, ingest events that change the problem state, decide whether those changes justify reoptimization, and publish a replacement only after the new candidate has been validated and shown to improve the configured objective.

The first reference problem is dynamic shortest-path optimization on a small directed network. Edge travel costs can change, edges can close or reopen, manual refresh requests can force a solve, and time-based refresh events can trigger periodic reoptimization. The architecture is intentionally domain-neutral so the same event/trigger/solve/validate pattern can later be reused for scheduling, allocation, inventory, dispatching, and other optimization problems.

## Architecture

```text
incoming event
    |
    v
state update
    |
    v
trigger policy ----> ignore event
    |
    v
optimizer
    |
    v
candidate solution
    |
    v
constraint validation
    |
    v
solution acceptance policy
    |
    v
current solution
```

## Design goals

- separate event ingestion from optimization logic;
- avoid unnecessary solver calls when changes are irrelevant;
- preserve hard feasibility constraints;
- support manual, event-driven, and periodic reoptimization;
- make every decision deterministic and testable for a fixed input state;
- expose optimization latency and solution-churn metrics;
- keep the optimization backend replaceable.

## Initial event model

The first version supports:

- `EDGE_COST_CHANGED`
- `EDGE_CLOSED`
- `EDGE_OPENED`
- `MANUAL_REOPTIMIZE`
- `TIMER_EXPIRED`

## Reoptimization policy

The engine does not blindly solve after every event. Reoptimization is triggered when at least one configured condition is met, for example:

- the current solution becomes infeasible;
- an event touches an edge used by the active path;
- a manual refresh is requested;
- the maximum allowed solution age is exceeded;
- a configured objective-degradation threshold is crossed.

This makes the project a reoptimization system rather than a loop that repeatedly runs a static solver.

## Optimization backends

Two shortest-path backends are included.

### Full recomputation

`DijkstraOptimizer` rebuilds the effective graph and solves the shortest-path problem from scratch. It is the deterministic correctness baseline.

### Incremental repair

`IncrementalShortestPathOptimizer` keeps shortest-path labels between solves. When an edge cost changes or an edge is closed/reopened, it detects the changed effective edge costs and repairs affected labels instead of intentionally discarding all previous search state. If graph topology or endpoints change, it safely falls back to full internal reinitialization.

The incremental implementation exposes diagnostic counters:

- `last_changed_edges`
- `last_expanded_vertices`

These make it possible to measure how much work is reused after each state change.

## Benchmark

Run a deterministic stream of changing edge costs against both implementations:

```bash
python -m continuous_reoptimization.benchmark --size 30 --events 250 --seed 42
```

To persist the report:

```bash
mkdir -p outputs
python -m continuous_reoptimization.benchmark \
  --size 30 \
  --events 250 \
  --seed 42 \
  --output outputs/benchmark.json
```

The report contains:

- graph node and edge counts;
- number of change events;
- total Dijkstra recomputation time;
- total incremental repair time;
- measured speedup;
- objective mismatches against the Dijkstra baseline;
- number of changed edges processed by the incremental solver;
- number of vertices expanded by incremental repair.

The benchmark fails if the incremental objective disagrees with the Dijkstra baseline. Runtime speedup is reported as an observation, not enforced as a CI assertion, because CI runner performance is noisy.

## Machine learning

Machine learning is optional rather than assumed. A predictive model may estimate future costs, demand, processing times, failure probabilities, or other changing coefficients, while the optimizer remains responsible for selecting a feasible decision from those inputs.

This keeps prediction and optimization as separate responsibilities and allows reactive optimization to be compared with predictive optimization later.

## Quality gates

CI runs unit tests, regression checks, Ruff, mypy, and coverage across supported Python versions. A separate scheduled/manual workflow runs the dynamic scenario tests and writes the Dijkstra-versus-incremental benchmark result to a GitHub Actions artifact.
