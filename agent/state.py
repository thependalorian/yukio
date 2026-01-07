"""
State definitions for Yukio agent orchestration.

This module defines the state structure used throughout the graph workflow.
State is shared between nodes and updated as the graph executes.
"""

from typing import TypedDict, Annotated, List, Optional, Dict, Any, Sequence, Union
import operator

try:
    from langchain_core.messages import BaseMessage
    LANGCHAIN_AVAILABLE = True
except ImportError:
    # Fallback for when langchain-core is not installed
    LANGCHAIN_AVAILABLE = False
    BaseMessage = Any  # type: ignore

# Note: resume_data field added to AgentState for LangGraph orchestration


class AgentState(TypedDict):
    """
    Main state for Yukio agent workflow.
    
    This state is passed between nodes and updated throughout execution.
    Messages are accumulated (using operator.add) to maintain conversation history.
    """
    # Messages in the conversation (accumulated)
    messages: Annotated[Sequence[BaseMessage], operator.add]
    
    # Current user input
    user_input: str
    
    # Session and user context
    session_id: str
    user_id: Optional[str]
    
    # Agent reasoning and tool execution
    agent_outcome: Optional[Dict[str, Any]]  # Latest agent response
    tool_calls: Annotated[List[Dict[str, Any]], operator.add]  # Accumulated tool calls
    tool_results: Annotated[List[Dict[str, Any]], operator.add]  # Accumulated tool results
    
    # Task classification and routing
    task_type: Optional[str]  # "language_learning", "career_coaching", "rirekisho", etc.
    needs_resume: bool  # Whether resume data is needed
    resume_data: Optional[List[Dict[str, Any]]]  # Loaded resume chunks from knowledge base
    
    # Validation and quality control
    validation_errors: List[str]
    needs_revision: bool
    
    # Metadata
    metadata: Dict[str, Any]


class RirekishoState(TypedDict):
    """
    Specialized state for rirekisho generation workflow.
    
    Used when generating Japanese resumes to track progress through sections.
    """
    # Base state
    messages: Annotated[Sequence[BaseMessage], operator.add]
    user_input: str
    session_id: str
    user_id: Optional[str]
    
    # Resume data
    resume_data: Optional[List[Dict[str, Any]]]
    job_context: Optional[Dict[str, Any]]  # job_title, company_name, job_description
    
    # Generation progress
    sections_completed: Annotated[List[str], operator.add]  # List of completed section names
    sections: Dict[str, str]  # section_name -> content
    current_section: Optional[str]
    
    # Validation
    validation_errors: List[str]
    is_complete: bool
    
    # Output
    final_output: Optional[str]


class ReasoningState(TypedDict):
    """
    State for ReAct reasoning loop.
    
    Tracks reasoning steps, observations, and iterations.
    """
    # Base state
    messages: Annotated[Sequence[BaseMessage], operator.add]
    task: str
    goal: str
    
    # Reasoning tracking
    reasoning_steps: Annotated[List[Dict[str, Any]], operator.add]
    observations: Annotated[List[str], operator.add]
    tool_results: Annotated[List[Dict[str, Any]], operator.add]
    
    # Iteration control
    iteration_count: int
    max_iterations: int
    status: str  # "pending", "in_progress", "validating", "completed", "failed"
    
    # Validation
    validation_errors: List[str]
    needs_revision: bool

