import json
from pathlib import Path
import networkx as nx


class KnowledgeGraph:
    """Simple wrapper around a NetworkX MultiDiGraph."""

    def __init__(self, path: str | Path | None = None) -> None:
        self.path = Path(path or "storage/knowledge_graph.graphml")
        self.graph = nx.MultiDiGraph()
        if self.path.exists():
            self.load_graph(self.path)

    def add_entity(self, entity: str) -> None:
        """Add a node for ``entity`` if it doesn't already exist."""
        if entity and entity not in self.graph:
            self.graph.add_node(entity)

    def add_relation(self, src: str, dst: str, relation: str) -> None:
        """Link ``src`` -> ``dst`` with ``relation`` label."""
        self.add_entity(src)
        self.add_entity(dst)
        self.graph.add_edge(src, dst, relation=relation)

    def get_neighbors(self, entity: str) -> list[tuple[str, str]]:
        """Return neighbors of ``entity`` with relation labels."""
        neighbors: list[tuple[str, str]] = []
        if entity in self.graph:
            for _, nbr, data in self.graph.edges(entity, data=True):
                neighbors.append((nbr, data.get("relation", "")))
        return neighbors

    def save_graph(self, path: str | Path | None = None) -> None:
        """Persist the graph to ``path`` in GraphML format."""
        p = Path(path or self.path)
        p.parent.mkdir(parents=True, exist_ok=True)
        nx.write_graphml(self.graph, p)

    def load_graph(self, path: str | Path | None = None) -> None:
        p = Path(path or self.path)
        if p.exists():
            self.graph = nx.read_graphml(p)

