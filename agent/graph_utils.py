"""
Graph utilities stub for backward compatibility.

NOTE: This module is a stub that maintains backward compatibility.
Yukio uses LanceDB for vector storage and Mem0 for memory instead of Neo4j/Graphiti.

For knowledge graph-like functionality, use:
- db_utils.py for vector search
- memory_utils.py for relationship/fact memory
"""

import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)


class GraphClientStub:
    """
    Stub class for backward compatibility.

    This replaces the GraphitiClient for projects that don't use Neo4j.
    All methods return empty results or no-ops.
    """

    def __init__(self):
        self._initialized = False
        logger.info("GraphClientStub initialized (Neo4j/Graphiti not in use)")

    async def initialize(self):
        """No-op initialization."""
        self._initialized = True

    async def close(self):
        """No-op close."""
        self._initialized = False

    async def search(self, query: str) -> List[Dict[str, Any]]:
        """Return empty search results."""
        logger.debug(f"Graph search stub called with: {query}")
        return []

    async def get_related_entities(
        self,
        entity_name: str,
        relationship_types: Optional[List[str]] = None,
        depth: int = 1
    ) -> Dict[str, Any]:
        """Return empty entity relationships."""
        return {
            "central_entity": entity_name,
            "related_facts": [],
            "search_method": "stub_not_implemented"
        }

    async def get_entity_timeline(
        self,
        entity_name: str,
        start_date=None,
        end_date=None
    ) -> List[Dict[str, Any]]:
        """Return empty timeline."""
        return []

    async def get_graph_statistics(self) -> Dict[str, Any]:
        """Return stub statistics."""
        return {
            "graphiti_initialized": False,
            "note": "Graph functionality not available - using LanceDB + Mem0"
        }


# Global stub instance
graph_client = GraphClientStub()


async def initialize_graph():
    """No-op initialization for backward compatibility."""
    await graph_client.initialize()


async def close_graph():
    """No-op close for backward compatibility."""
    await graph_client.close()


async def search_knowledge_graph(query: str) -> List[Dict[str, Any]]:
    """
    Stub for knowledge graph search.

    For actual search functionality, use:
    - db_utils.vector_search() for semantic search
    - memory_utils.recall() for memory search

    Args:
        query: Search query

    Returns:
        Empty list (stub)
    """
    logger.debug(f"search_knowledge_graph stub called: {query}")
    return []


async def get_entity_relationships(
    entity: str,
    depth: int = 2
) -> Dict[str, Any]:
    """
    Stub for entity relationships.

    Args:
        entity: Entity name
        depth: Traversal depth (ignored)

    Returns:
        Empty relationship dict (stub)
    """
    return await graph_client.get_related_entities(entity, depth=depth)


async def test_graph_connection() -> bool:
    """
    Stub for graph connection test.

    Returns:
        True (stub always succeeds)
    """
    logger.info("Graph connection test stub - returning True")
    return True
