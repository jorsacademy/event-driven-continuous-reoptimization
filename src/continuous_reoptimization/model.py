from dataclasses import dataclass, field

import networkx as nx

from .events import Edge


@dataclass(frozen=True, slots=True)
class RouteSolution:
    path: tuple[str, ...]
    objective: float

    @property
    def edges(self) -> tuple[Edge, ...]:
        return tuple(zip(self.path, self.path[1:]))


@dataclass(slots=True)
class OptimizationState:
    graph: nx.DiGraph
    origin: str
    destination: str
    closed_edges: set[Edge] = field(default_factory=set)
    version: int = 0

    def touch(self) -> None:
        self.version += 1
