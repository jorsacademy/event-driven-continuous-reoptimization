from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass, field

from .events import Edge


@dataclass(slots=True)
class EdgeCostPredictor:
    """Deterministic short-horizon predictor using recent edge-cost history.

    Prediction is a damped linear trend over the most recent observations. The
    class intentionally stays lightweight so prediction quality can be tested
    separately from optimization behavior.
    """

    window: int = 4
    trend_damping: float = 0.6
    _history: dict[Edge, deque[float]] = field(default_factory=lambda: defaultdict(deque))

    def observe(self, edge: Edge, cost: float) -> None:
        if cost < 0:
            raise ValueError("edge cost must be non-negative")
        history = self._history[edge]
        history.append(float(cost))
        while len(history) > self.window:
            history.popleft()

    def predict(self, edge: Edge, current_cost: float) -> float:
        history = self._history.get(edge)
        if history is None or len(history) < 2:
            return float(current_cost)

        values = list(history)
        trend = values[-1] - values[-2]
        predicted = values[-1] + self.trend_damping * trend
        return max(0.0, float(predicted))

    def history_size(self, edge: Edge) -> int:
        history = self._history.get(edge)
        return 0 if history is None else len(history)
