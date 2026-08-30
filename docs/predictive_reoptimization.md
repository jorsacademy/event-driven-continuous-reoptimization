# Predictive Reoptimization

Reactive optimization solves with the costs observed now. Predictive reoptimization inserts a forecasting layer before the optimizer and solves with estimated short-horizon costs.

```text
observations -> predictor -> projected edge costs -> optimizer -> decision
```

The prediction layer and optimization layer are intentionally separate. The included `EdgeCostPredictor` uses a deterministic damped recent-trend forecast, while `PredictiveDijkstraOptimizer` projects those estimates onto a copy of the current graph and solves that projected state with the Dijkstra correctness baseline.

The live optimization state is not mutated by prediction.

## Evaluation protocol

The reactive-versus-predictive benchmark avoids look-ahead leakage:

1. At step `t`, both methods see only the current and historical observations.
2. The reactive method optimizes on current costs.
3. The predictive method estimates `t+1` costs from history and optimizes on those estimates.
4. Both selected paths are scored using the costs that actually occur at `t+1`.
5. The process repeats as a rolling horizon.

This produces a decision-focused evaluation: prediction is valuable only when it improves the realized optimization objective.

Run:

```bash
python -m continuous_reoptimization.predictive_benchmark --steps 24
```

The report includes cumulative next-step realized cost and path-switch counts for both policies, plus the predictive improvement percentage.

This predictor is deliberately simple. Future extensions can replace it with exponential smoothing, online regression, gradient boosting, recurrent models, or probabilistic forecasts without changing the optimizer interface.
