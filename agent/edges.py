"""
Edge and conditional edge logic for Yukio agent graph.

Edges determine the flow of execution between nodes.
Conditional edges use logic to route based on state.
"""

import logging
from typing import Literal
from .state import AgentState

logger = logging.getLogger(__name__)


def should_load_resume(state: AgentState) -> Literal["load_resume", "skip_resume"]:
    """
    Conditional edge: Determine if resume data should be loaded.
    
    Returns:
        "load_resume" if resume data is needed
        "skip_resume" if not needed
    """
    needs_resume = state.get("needs_resume", False)
    resume_data = state.get("resume_data")
    
    # Load if needed and not already loaded
    if needs_resume and not resume_data:
        logger.info("Routing to load_resume node")
        return "load_resume"
    
    logger.info("Skipping resume load")
    return "skip_resume"


def should_validate(state: AgentState) -> Literal["validate", "skip_validation"]:
    """
    Conditional edge: Determine if output should be validated.
    
    Returns:
        "validate" for complex tasks that need validation
        "skip_validation" for simple tasks
    """
    task_type = state.get("task_type", "general")
    
    # Validate complex tasks
    if task_type in ["rirekisho_generation", "shokumu_generation"]:
        logger.info("Routing to validate node")
        return "validate"
    
    logger.info("Skipping validation")
    return "skip_validation"


def should_revise(state: AgentState) -> Literal["revise", "complete"]:
    """
    Conditional edge: Determine if output needs revision.
    
    Returns:
        "revise" if validation found errors
        "complete" if output is acceptable
    """
    needs_revision = state.get("needs_revision", False)
    validation_errors = state.get("validation_errors", [])
    
    if needs_revision and validation_errors:
        logger.info(f"Routing to revise node ({len(validation_errors)} errors)")
        return "revise"
    
    logger.info("Output complete, no revision needed")
    return "complete"


def route_after_resume(state: AgentState) -> Literal["agent", "error"]:
    """
    Conditional edge: Route after resume loading.
    
    Returns:
        "agent" if resume loaded successfully
        "error" if resume loading failed
    """
    resume_data = state.get("resume_data", [])
    metadata = state.get("metadata", {})
    
    if metadata.get("resume_loaded", False) or len(resume_data) > 0:
        logger.info("Resume loaded, routing to agent")
        return "agent"
    
    logger.warning("Resume loading failed, routing to error handling")
    return "error"


def route_after_validation(state: AgentState) -> Literal["revise", "complete"]:
    """
    Conditional edge: Route after validation.
    
    Returns:
        "revise" if validation failed
        "complete" if validation passed
    """
    needs_revision = state.get("needs_revision", False)
    
    if needs_revision:
        logger.info("Validation failed, routing to revise")
        return "revise"
    
    logger.info("Validation passed, completing")
    return "complete"


def route_after_revision(state: AgentState) -> Literal["validate", "complete"]:
    """
    Conditional edge: Route after revision.
    
    Returns:
        "validate" to re-validate revised output
        "complete" if revision successful
    """
    needs_revision = state.get("needs_revision", False)
    
    if needs_revision:
        logger.info("Still needs revision, routing back to validate")
        return "validate"
    
    logger.info("Revision successful, completing")
    return "complete"

