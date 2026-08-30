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

## Development plan

The first implementation will use Dijkstra as a deterministic baseline. Later iterations can add incremental shortest-path methods, rolling-horizon formulations, warm starts, anytime optimization, and predictive models that estimate changing objective coefficients before the optimization stage.

Machine learning is therefore optional rather than assumed: prediction and optimization remain separate responsibilities.

## Quality gates

The repository is intended to include unit tests, regression scenarios, static checks, coverage reporting, and GitHub Actions workflows for push/PR validation, scheduled simulation runs, and manual benchmark execution.
