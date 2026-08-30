from dataclasses import dataclass

from .events import EdgeClosed, EdgeCostChanged, EdgeOpened, Event
from .model import OptimizationState, RouteSolution
from .optimizer import DijkstraOptimizer, NoFeasibleRouteError
from .policy import TriggerPolicy


@dataclass(frozen=True, slots=True)
class EventResult:
    reoptimized: bool
    accepted: bool
    solution: RouteSolution | None
    state_version: int


class ReoptimizationEngine:
    def __init__(
        self,
        state: OptimizationState,
        optimizer: DijkstraOptimizer | None = None,
        policy: TriggerPolicy | None = None,
    ) -> None:
        self.state = state
        self.optimizer = optimizer or DijkstraOptimizer()
        self.policy = policy or TriggerPolicy()
        self.current_solution: RouteSolution | None = None
        self.solve_count = 0

    def optimize(self) -> RouteSolution:
        solution = self.optimizer.solve(self.state)
        self.current_solution = solution
        self.solve_count += 1
        return solution

    def handle(self, event: Event) -> EventResult:
        self._apply_event(event)
        should_solve = self.policy.should_reoptimize(event, self.current_solution)
        if not should_solve:
            return EventResult(False, False, self.current_solution, self.state.version)

        self.solve_count += 1
        try:
            candidate = self.optimizer.solve(self.state)
        except NoFeasibleRouteError:
            self.current_solution = None
            return EventResult(True, False, None, self.state.version)

        self.current_solution = candidate
        return EventResult(True, True, candidate, self.state.version)

    def _apply_event(self, event: Event) -> None:
        if isinstance(event, EdgeCostChanged):
            u, v = event.edge
            if not self.state.graph.has_edge(u, v):
                raise KeyError(f"unknown edge: {event.edge}")
            if event.new_cost < 0:
                raise ValueError("edge cost must be non-negative for Dijkstra")
            self.state.graph[u][v]["cost"] = float(event.new_cost)
        elif isinstance(event, EdgeClosed):
            if not self.state.graph.has_edge(*event.edge):
                raise KeyError(f"unknown edge: {event.edge}")
            self.state.closed_edges.add(event.edge)
        elif isinstance(event, EdgeOpened):
            if not self.state.graph.has_edge(*event.edge):
                raise KeyError(f"unknown edge: {event.edge}")
            self.state.closed_edges.discard(event.edge)
        self.state.touch()
