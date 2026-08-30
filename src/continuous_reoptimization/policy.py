from dataclasses import dataclass

from .events import EdgeClosed, EdgeCostChanged, EdgeOpened, Event, ManualReoptimize, TimerExpired
from .model import RouteSolution


@dataclass(frozen=True, slots=True)
class TriggerPolicy:
    max_solution_age_seconds: float = 60.0

    def should_reoptimize(self, event: Event, current: RouteSolution | None) -> bool:
        if current is None:
            return True
        if isinstance(event, (ManualReoptimize, EdgeOpened)):
            return True
        if isinstance(event, TimerExpired):
            return event.elapsed_seconds >= self.max_solution_age_seconds
        if isinstance(event, (EdgeClosed, EdgeCostChanged)):
            return event.edge in current.edges
        return False
