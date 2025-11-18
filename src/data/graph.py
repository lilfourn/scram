import logging
import uuid
from typing import Any, Dict, List, Set, Tuple, Optional
import json
import networkx as nx

logger = logging.getLogger(__name__)


class KnowledgeGraph:
    def __init__(self):
        self.graph = nx.MultiDiGraph()
        self.entity_index: Dict[str, str] = {}  # Map unique keys to Node IDs

    def add_entity(self, entity_type: str, properties: Dict[str, Any]) -> str:
        """
        Add an entity to the graph. Returns the Node ID.
        Performs basic deduplication based on unique keys if present.
        """
        # Identify unique key
        unique_key = self._get_unique_key(entity_type, properties)

        if unique_key and unique_key in self.entity_index:
            # Merge properties
            node_id = self.entity_index[unique_key]
            self.graph.nodes[node_id].update(properties)
            return node_id

        node_id = str(uuid.uuid4())
        self.graph.add_node(node_id, type=entity_type, **properties)

        if unique_key:
            self.entity_index[unique_key] = node_id

        return node_id

    def add_relationship(
        self,
        source_id: str,
        target_id: str,
        relation_type: str,
        properties: Dict[str, Any] = None,
    ):
        """Add a directed edge between two entities."""
        if not self.graph.has_node(source_id) or not self.graph.has_node(target_id):
            logger.warning(f"Cannot add relationship {relation_type}: nodes not found.")
            return

        self.graph.add_edge(
            source_id,
            target_id,
            key=relation_type,
            type=relation_type,
            **(properties or {}),
        )

    def _get_unique_key(
        self, entity_type: str, properties: Dict[str, Any]
    ) -> Optional[str]:
        """Generate a unique key for deduplication."""
        # Priority keys
        for key in ["url", "id", "isbn", "sku", "email"]:
            if key in properties and properties[key]:
                return f"{entity_type}:{key}:{properties[key]}"

        # Fallback: Name + Type (weak identity)
        if "name" in properties:
            return f"{entity_type}:name:{properties['name'].lower().strip()}"

        return None

    def resolve_entities(self):
        """
        Merge duplicate entities based on similarity.
        (Placeholder for vector-based resolution)
        """
        # For now, we rely on _get_unique_key during insertion.
        # Future: Use Faiss/Embeddings to find similar nodes and merge them.
        pass

    def export_graphml(self, path: str):
        """Export the graph to GraphML format."""
        try:
            # NetworkX GraphML writer requires attributes to be scalar or simple types.
            # We need to serialize complex dicts/lists to strings.
            G_export = self.graph.copy()
            for node, data in G_export.nodes(data=True):
                for k, v in data.items():
                    if isinstance(v, (dict, list)):
                        data[k] = json.dumps(v)

            nx.write_graphml(G_export, path)
            logger.info(f"Graph exported to {path}")
        except Exception as e:
            logger.error(f"Failed to export GraphML: {e}")

    def to_json(self) -> Dict[str, Any]:
        """Return graph as JSON node-link data."""
        return nx.node_link_data(self.graph)
