from dataclasses import dataclass

Edge = tuple[str, str]


@dataclass(frozen=True, slots=True)
class EdgeCostChanged:
    edge: Edge
    new_cost: float


@dataclass(frozen=True, slots=True)
class EdgeClosed:
    edge: Edge


@dataclass(frozen=True, slots=True)
class EdgeOpened:
    edge: Edge


@dataclass(frozen=True, slots=True)
class ManualReoptimize:
    reason: str = "manual refresh"


@dataclass(frozen=True, slots=True)
class TimerExpired:
    elapsed_seconds: float


Event = EdgeCostChanged | EdgeClosed | EdgeOpened | ManualReoptimize | TimerExpired
