import networkx as nx

from .model import OptimizationState, RouteSolution


class NoFeasibleRouteError(RuntimeError):
    pass


class DijkstraOptimizer:
    def solve(self, state: OptimizationState) -> RouteSolution:
        graph = state.graph.copy()
        graph.remove_edges_from(state.closed_edges)
        try:
            path = nx.shortest_path(
                graph,
                state.origin,
                state.destination,
                weight="cost",
                method="dijkstra",
            )
        except (nx.NetworkXNoPath, nx.NodeNotFound) as exc:
            raise NoFeasibleRouteError("no feasible route exists") from exc

        objective = nx.path_weight(graph, path, weight="cost")
        return RouteSolution(tuple(path), float(objective))
