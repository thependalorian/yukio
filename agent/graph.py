"""
Graph construction and compilation for Yukio agent.

This module builds the LangGraph workflow by:
1. Creating the state graph
2. Adding nodes
3. Adding edges (normal and conditional)
4. Compiling the graph
"""

import logging
from typing import Optional, Any

logger = logging.getLogger(__name__)

try:
    from langgraph.graph import StateGraph, END
    # Try to import SqliteSaver, fallback to MemorySaver
    try:
        from langgraph.checkpoint.sqlite import SqliteSaver
    except ImportError:
        # Use MemorySaver as fallback (in-memory checkpointer)
        from langgraph.checkpoint.memory import MemorySaver
        SqliteSaver = MemorySaver  # Alias for compatibility
    LANGGRAPH_AVAILABLE = True
except ImportError:
    LANGGRAPH_AVAILABLE = False
    StateGraph = None
    END = None
    SqliteSaver = None
    logger.warning("LangGraph not installed. Install with: uv pip install langgraph langchain-core")

from .state import AgentState
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


def create_agent_graph(checkpointer: Optional[Any] = None) -> Any:
    """
    Create and compile the main Yukio agent graph.
    
    Graph structure:
    1. classify_task -> determines task type and routing
    2. Conditional: should_load_resume?
       - load_resume -> loads resume data if needed
       - skip_resume -> continues without resume
    3. agent -> executes PydanticAI agent
    4. Conditional: should_validate?
       - validate -> validates output
       - skip_validation -> completes
    5. Conditional: should_revise?
       - revise -> fixes errors
       - complete -> END
    
    Args:
        checkpointer: Optional checkpointer for state persistence
    
    Returns:
        Compiled StateGraph ready for execution
    """
    if not LANGGRAPH_AVAILABLE:
        raise ImportError("LangGraph is required. Install with: pip install langgraph langchain-core")
    
    # Create graph with AgentState
    graph = StateGraph(AgentState)
    
    # Add nodes
    graph.add_node("classify_task", classify_task_node)
    graph.add_node("load_resume", load_resume_node)
    graph.add_node("agent", agent_node)
    graph.add_node("validate", validate_output_node)
    graph.add_node("revise", revise_output_node)
    
    # Set entry point
    graph.set_entry_point("classify_task")
    
    # Add edges from classify_task
    graph.add_conditional_edges(
        "classify_task",
        should_load_resume,
        {
            "load_resume": "load_resume",
            "skip_resume": "agent"
        }
    )
    
    # Add edges from load_resume
    graph.add_conditional_edges(
        "load_resume",
        route_after_resume,
        {
            "agent": "agent",
            "error": "agent"  # Continue even if resume load fails
        }
    )
    
    # Add edge from agent to validation check
    graph.add_conditional_edges(
        "agent",
        should_validate,
        {
            "validate": "validate",
            "skip_validation": END
        }
    )
    
    # Add edges from validate
    graph.add_conditional_edges(
        "validate",
        route_after_validation,
        {
            "revise": "revise",
            "complete": END
        }
    )
    
    # Add edges from revise
    graph.add_conditional_edges(
        "revise",
        route_after_revision,
        {
            "validate": "validate",  # Re-validate after revision
            "complete": END
        }
    )
    
    # Compile graph
    if checkpointer:
        compiled_graph = graph.compile(checkpointer=checkpointer)
    else:
        # Use in-memory checkpointer for development
        # Try SqliteSaver first, fallback to MemorySaver
        try:
            if hasattr(SqliteSaver, 'from_conn_string'):
                checkpointer = SqliteSaver.from_conn_string(":memory:")
            else:
                # MemorySaver doesn't have from_conn_string, instantiate directly
                checkpointer = SqliteSaver()
        except Exception:
            # Fallback to MemorySaver
            from langgraph.checkpoint.memory import MemorySaver
            checkpointer = MemorySaver()
        compiled_graph = graph.compile(checkpointer=checkpointer)
    
    logger.info("Agent graph compiled successfully")
    return compiled_graph


# Global graph instance (lazy initialization)
_agent_graph = None


def get_agent_graph(checkpointer: Optional[Any] = None) -> Any:
    """
    Get or create the agent graph instance.
    
    Args:
        checkpointer: Optional checkpointer for state persistence
    
    Returns:
        Compiled StateGraph instance
    """
    global _agent_graph
    
    if _agent_graph is None:
        _agent_graph = create_agent_graph(checkpointer)
    
    return _agent_graph

