"""
Node implementations for Yukio agent graph.

Nodes are the executable units in the graph that perform specific actions.
Each node receives state, performs work, and returns updated state.
"""

import logging
from typing import Dict, Any

try:
    from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False
    # Create simple message classes as fallback
    class HumanMessage:
        def __init__(self, content: str):
            self.content = content
    class AIMessage:
        def __init__(self, content: str):
            self.content = content
    class SystemMessage:
        def __init__(self, content: str):
            self.content = content

from .state import AgentState, RirekishoState, ReasoningState
from .agent import rag_agent, AgentDependencies
from .tools import get_resume_tool, GetResumeInput
try:
    from .reasoning import get_validator_for_task, RIREKISHO_VALIDATOR
except ImportError:
    # Fallback if reasoning module not available
    RIREKISHO_VALIDATOR = None
    def get_validator_for_task(task: str):
        return None

logger = logging.getLogger(__name__)


async def classify_task_node(state: AgentState) -> Dict[str, Any]:
    """
    Classify the task type and determine routing.
    
    Analyzes user input to determine if this is:
    - Language learning question
    - Career coaching / resume question
    - Rirekisho generation
    - General conversation
    """
    user_input = state.get("user_input", "")
    user_input_lower = user_input.lower()
    
    # Detect task type
    task_type = "general"
    needs_resume = False
    
    # Resume/career keywords
    resume_keywords = [
        'resume', 'cv', 'rirekisho', 'shokumu-keirekisho', 
        'career', 'work experience', 'job application', 
        'work history', 'buffr', 'previous job', 'education background'
    ]
    
    # Rirekisho generation keywords
    rirekisho_keywords = [
        'create rirekisho', 'generate rirekisho', 'create shokumu',
        'generate shokumu', '履歴書を作成', '職務経歴書を作成'
    ]
    
    if any(keyword in user_input_lower for keyword in rirekisho_keywords):
        task_type = "rirekisho_generation"
        needs_resume = True
    elif any(keyword in user_input_lower for keyword in resume_keywords):
        task_type = "career_coaching"
        needs_resume = True
    elif any(word in user_input_lower for word in ['learn', 'practice', 'grammar', 'vocabulary', 'kanji', 'hiragana']):
        task_type = "language_learning"
    
    logger.info(f"Task classified as: {task_type}, needs_resume: {needs_resume}")
    
    return {
        "task_type": task_type,
        "needs_resume": needs_resume
    }


async def load_resume_node(state: AgentState) -> Dict[str, Any]:
    """
    Load resume data from knowledge base.
    
    This node retrieves George's resume information using the get_resume tool.
    """
    try:
        user_id = state.get("user_id", "george_nekwaya")
        
        # Use get_resume_tool to fetch resume data
        input_data = GetResumeInput(
            query="George Nekwaya resume work experience education skills Buffr",
            limit=15
        )
        
        resume_results = await get_resume_tool(input_data)
        
        # Convert to dict format
        resume_data = [
            {
                "content": r.content,
                "score": r.score,
                "document_title": r.document_title,
                "document_source": r.document_source,
                "chunk_id": r.chunk_id,
                "metadata": r.metadata
            }
            for r in resume_results
        ]
        
        logger.info(f"Loaded {len(resume_data)} resume chunks")
        
        return {
            "resume_data": resume_data,
            "metadata": {
                **state.get("metadata", {}),
                "resume_loaded": True,
                "resume_chunks": len(resume_data)
            }
        }
    except Exception as e:
        logger.error(f"Failed to load resume: {e}")
        return {
            "resume_data": [],
            "metadata": {
                **state.get("metadata", {}),
                "resume_loaded": False,
                "resume_error": str(e)
            }
        }


async def agent_node(state: AgentState) -> Dict[str, Any]:
    """
    Execute the PydanticAI agent with current state.
    
    This node calls the rag_agent with the user input and context,
    then updates state with the agent's response and tool calls.
    """
    try:
        user_input = state.get("user_input", "")
        session_id = state.get("session_id", "default")
        user_id = state.get("user_id")
        
        # Build context from messages
        messages = state.get("messages", [])
        context_parts = []
        
        # Add resume data if available
        resume_data = state.get("resume_data")
        if resume_data:
            resume_context = "\n\n".join([
                f"**{r.get('document_title', 'Resume')}**\n{r.get('content', '')}"
                for r in resume_data[:5]
            ])
            context_parts.append(f"RESUME CONTEXT:\n{resume_context}")
        
        # Add conversation history
        if messages:
            context_parts.append("CONVERSATION HISTORY:")
            for msg in messages[-6:]:  # Last 6 messages
                if hasattr(msg, 'content'):
                    role = "User" if isinstance(msg, HumanMessage) else "Assistant"
                    context_parts.append(f"{role}: {msg.content}")
        
        # Build full prompt
        if context_parts:
            full_prompt = "\n\n".join(context_parts) + f"\n\nCurrent question: {user_input}"
        else:
            full_prompt = user_input
        
        # Create dependencies
        deps = AgentDependencies(
            session_id=session_id,
            user_id=user_id
        )
        
        # Run agent
        result = await rag_agent.run(full_prompt, deps=deps)
        
        # Extract response
        try:
            response_text = result.output
        except AttributeError:
            response_text = str(result)
        
        # Extract tool calls if available
        tool_calls = []
        if hasattr(result, 'tool_calls'):
            tool_calls = result.tool_calls
        
        # Create AI message
        ai_message = AIMessage(content=response_text)
        
        logger.info(f"Agent response generated: {len(response_text)} chars, {len(tool_calls)} tool calls")
        
        return {
            "agent_outcome": {
                "response": response_text,
                "tool_calls": tool_calls
            },
            "messages": [ai_message],
            "tool_calls": [
                {
                    "tool_name": tc.get("tool_name", "unknown"),
                    "args": tc.get("args", {}),
                    "tool_call_id": tc.get("tool_call_id", "")
                }
                for tc in tool_calls
            ]
        }
    except Exception as e:
        logger.error(f"Agent node failed: {e}", exc_info=True)
        error_message = AIMessage(content=f"I encountered an error: {str(e)}")
        return {
            "agent_outcome": {
                "response": f"Error: {str(e)}",
                "error": True
            },
            "messages": [error_message]
        }


async def validate_output_node(state: AgentState) -> Dict[str, Any]:
    """
    Validate agent output against requirements.
    
    Checks if output meets quality standards, especially for rirekisho generation.
    """
    task_type = state.get("task_type", "general")
    agent_outcome = state.get("agent_outcome", {})
    response = agent_outcome.get("response", "")
    
    validation_errors = []
    needs_revision = False
    
    # Validate rirekisho generation
    if task_type == "rirekisho_generation":
        validator = RIREKISHO_VALIDATOR
        
        # Try to parse response as structured output
        output_dict = _parse_response_to_dict(response, validator)
        is_valid, errors = validator.validate(output_dict)
        
        if not is_valid:
            validation_errors = errors
            needs_revision = True
            logger.warning(f"Validation failed: {errors}")
    
    # General quality checks
    if len(response) < 50:
        validation_errors.append("Response too short")
        needs_revision = True
    
    return {
        "validation_errors": validation_errors,
        "needs_revision": needs_revision
    }


async def revise_output_node(state: AgentState) -> Dict[str, Any]:
    """
    Revise output based on validation errors.
    
    This node calls the agent again with validation feedback to fix issues.
    """
    validation_errors = state.get("validation_errors", [])
    user_input = state.get("user_input", "")
    session_id = state.get("session_id", "default")
    user_id = state.get("user_id")
    
    # Build revision prompt
    revision_prompt = f"""The previous response had validation errors. Please fix them.

Original request: {user_input}

Validation errors:
{chr(10).join(f"- {error}" for error in validation_errors)}

Please regenerate the response, ensuring all requirements are met."""
    
    deps = AgentDependencies(
        session_id=session_id,
        user_id=user_id
    )
    
    try:
        result = await rag_agent.run(revision_prompt, deps=deps)
        response_text = result.output if hasattr(result, 'output') else str(result)
        
        revised_message = AIMessage(content=response_text)
        
        return {
            "agent_outcome": {
                "response": response_text,
                "revised": True
            },
            "messages": [revised_message],
            "needs_revision": False
        }
    except Exception as e:
        logger.error(f"Revision failed: {e}")
        return {
            "needs_revision": True,
            "validation_errors": [f"Revision failed: {str(e)}"]
        }


def _parse_response_to_dict(response: str, validator) -> Dict[str, Any]:
    """Parse agent response into structured dict for validation."""
    output_dict = {}
    
    # Try to extract sections based on validator requirements
    for field in validator.required_fields:
        # Look for section headers
        patterns = [
            field,
            field.replace("・", "・?"),
            field.split("(")[0].strip()
        ]
        
        for pattern in patterns:
            if pattern in response:
                start_idx = response.find(pattern)
                if start_idx != -1:
                    remaining = response[start_idx + len(pattern):]
                    next_section_idx = len(remaining)
                    
                    for other_field in validator.required_fields:
                        if other_field != field and other_field in remaining:
                            next_idx = remaining.find(other_field)
                            if next_idx != -1 and next_idx < next_section_idx:
                                next_section_idx = next_idx
                    
                    content = remaining[:next_section_idx].strip()
                    content = content.lstrip(":：").strip()
                    if content:
                        output_dict[field] = content
                        break
    
    if not output_dict:
        output_dict["content"] = response
    
    return output_dict

