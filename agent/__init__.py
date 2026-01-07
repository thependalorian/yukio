"""
Yukio - Local AI Japanese Tutor Agent Package.

This package provides:
- PydanticAI agent for Japanese language learning
- LangGraph orchestration for complex workflows
- RAG tools for knowledge retrieval
- Career coaching capabilities
"""

from .agent import rag_agent, AgentDependencies

# Optional LangGraph exports
try:
    from .graph import get_agent_graph, create_agent_graph
    from .state import AgentState, RirekishoState, ReasoningState
    from .nodes import (
        classify_task_node,
        load_resume_node,
        agent_node,
        validate_output_node,
        revise_output_node
    )
    from .edges import (
        should_load_resume,
        should_validate,
        should_revise,
        route_after_resume,
        route_after_validation,
        route_after_revision
    )
    LANGGRAPH_AVAILABLE = True
except ImportError:
    LANGGRAPH_AVAILABLE = False

__all__ = [
    "rag_agent",
    "AgentDependencies",
]

if LANGGRAPH_AVAILABLE:
    __all__.extend([
        "get_agent_graph",
        "create_agent_graph",
        "AgentState",
        "RirekishoState",
        "ReasoningState",
        "classify_task_node",
        "load_resume_node",
        "agent_node",
        "validate_output_node",
        "revise_output_node",
        "should_load_resume",
        "should_validate",
        "should_revise",
        "route_after_resume",
        "route_after_validation",
        "route_after_revision",
    ])
