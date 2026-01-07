"""
ReAct executor for complex tasks requiring reasoning and validation.

This module implements the ReAct pattern execution loop for tasks like
rirekisho generation that require multiple steps and validation.
"""

import logging
from typing import Dict, Any, Optional, AsyncGenerator
from .agent import rag_agent, AgentDependencies
from .reasoning import (
    ReasoningState,
    ReasoningStep,
    TaskStatus,
    create_reasoning_prompt,
    create_validation_prompt,
    decompose_task,
    should_continue_reasoning,
    get_validator_for_task
)

logger = logging.getLogger(__name__)


async def execute_react_task(
    task: str,
    user_message: str,
    session_id: str,
    user_id: Optional[str] = None,
    stream: bool = False
) -> AsyncGenerator[Dict[str, Any], None]:
    """
    Execute a task using ReAct (Reasoning + Acting) pattern.
    
    This implements a reasoning loop:
    1. THINK: Analyze what needs to be done
    2. ACT: Execute tools or generate content
    3. OBSERVE: Review results
    4. VALIDATE: Check if output meets requirements
    5. Repeat until complete
    
    Args:
        task: The task description
        user_message: Original user message
        session_id: Session identifier
        user_id: User identifier
        stream: Whether to stream responses
    
    Yields:
        Dict with type and content for streaming
    """
    # Initialize reasoning state
    state = ReasoningState(
        task=task,
        goal=user_message,
        status=TaskStatus.PENDING,
        max_iterations=15
    )
    
    # Decompose task into steps
    sub_tasks = decompose_task(task)
    state.add_step(
        ReasoningStep.THINK,
        f"Task decomposed into {len(sub_tasks)} steps: {', '.join(sub_tasks[:3])}..."
    )
    
    # Get validator if applicable
    validator = get_validator_for_task(task)
    if validator:
        state.add_step(
            ReasoningStep.THINK,
            f"Validation rules loaded: {len(validator.required_fields)} required fields, "
            f"language={validator.language_requirement}"
        )
    
    # ReAct loop
    while should_continue_reasoning(state):
        state.iteration_count += 1
        state.status = TaskStatus.IN_PROGRESS
        
        logger.info(f"ReAct iteration {state.iteration_count}/{state.max_iterations}")
        
        # THINK: Create reasoning prompt
        reasoning_prompt = create_reasoning_prompt(state)
        
        # Add system context
        full_prompt = f"""You are executing a complex task that requires reasoning and validation.

{reasoning_prompt}

**Instructions:**
1. Analyze the current state and what needs to be done next
2. If you need information, use appropriate tools (e.g., get_resume for resume data)
3. Generate the required content based on the task
4. Be thorough and complete - don't skip sections
5. If there are validation errors, fix them immediately

**Current Task**: {task}
**User Request**: {user_message}

Now proceed with the next step in the reasoning loop."""
        
        # ACT: Execute agent with reasoning prompt
        deps = AgentDependencies(
            session_id=session_id,
            user_id=user_id
        )
        
        if stream:
            yield {
                "type": "reasoning_step",
                "step": state.iteration_count,
                "content": f"Thinking step {state.iteration_count}..."
            }
        
        try:
            # Run agent
            result = await rag_agent.run(full_prompt, deps=deps)
            
            # Extract response
            try:
                response_text = result.output
            except AttributeError:
                response_text = str(result)
            
            # OBSERVE: Add observation
            state.add_observation(f"Agent response received: {response_text[:200]}...")
            
            # Check for tool calls in result
            if hasattr(result, 'tool_calls') and result.tool_calls:
                for tool_call in result.tool_calls:
                    tool_name = getattr(tool_call, 'tool_name', 'unknown')
                    state.add_tool_result(tool_name, "Tool executed")
                    state.add_observation(f"Tool {tool_name} was called")
            
            # VALIDATE: If we have a validator and this looks like final output
            if validator and state.iteration_count >= 3:
                # Try to parse response as structured output
                output_dict = _parse_response_to_dict(response_text, validator)
                
                is_valid, errors = validator.validate(output_dict)
                
                if is_valid:
                    state.status = TaskStatus.COMPLETED
                    state.add_step(
                        ReasoningStep.VALIDATE,
                        "✅ Validation passed! All requirements met."
                    )
                    
                    if stream:
                        yield {
                            "type": "validation",
                            "status": "passed",
                            "content": "All validation checks passed"
                        }
                        yield {
                            "type": "final_output",
                            "content": response_text
                        }
                    else:
                        yield {
                            "type": "final_output",
                            "content": response_text,
                            "validated": True
                        }
                    break
                else:
                    state.validation_errors = errors
                    state.status = TaskStatus.NEEDS_REVISION
                    state.add_step(
                        ReasoningStep.VALIDATE,
                        f"❌ Validation failed: {len(errors)} errors found"
                    )
                    
                    if stream:
                        yield {
                            "type": "validation",
                            "status": "failed",
                            "errors": errors,
                            "content": f"Validation found {len(errors)} issues. Fixing..."
                        }
                    
                    # Continue loop to fix errors
                    continue
            
            # If no validator or early iteration, check if task seems complete
            if not validator:
                # Simple completion check
                if _is_task_complete(response_text, task):
                    state.status = TaskStatus.COMPLETED
                    state.add_step(
                        ReasoningStep.COMPLETE,
                        "Task appears complete"
                    )
                    
                    if stream:
                        yield {
                            "type": "final_output",
                            "content": response_text
                        }
                    else:
                        yield {
                            "type": "final_output",
                            "content": response_text
                        }
                    break
            
            # Stream intermediate result
            if stream:
                yield {
                    "type": "intermediate",
                    "step": state.iteration_count,
                    "content": response_text
                }
            
        except Exception as e:
            logger.error(f"Error in ReAct iteration {state.iteration_count}: {e}", exc_info=True)
            state.add_observation(f"Error occurred: {str(e)}")
            
            if state.iteration_count >= state.max_iterations:
                state.status = TaskStatus.FAILED
                yield {
                    "type": "error",
                    "content": f"Task failed after {state.iteration_count} iterations: {str(e)}"
                }
                break
    
    # Final status
    if state.status != TaskStatus.COMPLETED:
        logger.warning(f"Task ended with status: {state.status}")
        yield {
            "type": "status",
            "status": state.status.value,
            "iterations": state.iteration_count,
            "validation_errors": state.validation_errors
        }


def _parse_response_to_dict(response: str, validator) -> Dict[str, Any]:
    """Parse agent response into structured dict for validation."""
    output_dict = {}
    
    # Try to extract sections based on validator requirements
    for field in validator.required_fields:
        # Look for section headers
        patterns = [
            field,
            field.replace("・", "・?"),  # Flexible matching
            field.split("(")[0].strip()  # Without parentheses
        ]
        
        for pattern in patterns:
            if pattern in response:
                # Extract content after this section
                start_idx = response.find(pattern)
                if start_idx != -1:
                    # Find next section or end
                    remaining = response[start_idx + len(pattern):]
                    # Look for next section marker
                    next_section_idx = len(remaining)
                    for other_field in validator.required_fields:
                        if other_field != field and other_field in remaining:
                            next_idx = remaining.find(other_field)
                            if next_idx != -1 and next_idx < next_section_idx:
                                next_section_idx = next_idx
                    
                    content = remaining[:next_section_idx].strip()
                    # Clean up content
                    content = content.lstrip(":：").strip()
                    if content:
                        output_dict[field] = content
                        break
    
    # If we couldn't parse, use full response as content
    if not output_dict:
        output_dict["content"] = response
    
    return output_dict


def _is_task_complete(response: str, task: str) -> bool:
    """Simple heuristic to check if task appears complete."""
    task_lower = task.lower()
    
    if "rirekisho" in task_lower:
        # Check for key sections
        required_sections = ["職務要約", "自己PR", "志望動機"]
        return all(section in response for section in required_sections)
    
    if "shokumu" in task_lower:
        required_sections = ["経歴要約", "職務内容", "自己PR"]
        return all(section in response for section in required_sections)
    
    # Generic: check if response is substantial
    return len(response) > 500

