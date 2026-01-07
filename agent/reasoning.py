"""
ReAct (Reasoning + Acting) pattern implementation for Yukio agent.

This module implements:
- Prompt chaining for complex tasks
- Output validation
- Reasoning loops (think → act → observe → think)
- Step-by-step task decomposition
"""

import logging
from typing import Dict, Any, List, Optional, Callable, Tuple
from enum import Enum
from dataclasses import dataclass, field
from pydantic import BaseModel, Field, field_validator

logger = logging.getLogger(__name__)


class ReasoningStep(str, Enum):
    """Reasoning step types in ReAct pattern."""
    THINK = "think"
    ACT = "act"
    OBSERVE = "observe"
    VALIDATE = "validate"
    COMPLETE = "complete"


class TaskStatus(str, Enum):
    """Task execution status."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    VALIDATING = "validating"
    COMPLETED = "completed"
    FAILED = "failed"
    NEEDS_REVISION = "needs_revision"


@dataclass
class ReasoningState:
    """State tracking for ReAct reasoning loop."""
    task: str
    goal: str
    steps: List[Dict[str, Any]] = field(default_factory=list)
    current_step: int = 0
    observations: List[str] = field(default_factory=list)
    tool_results: List[Dict[str, Any]] = field(default_factory=list)
    status: TaskStatus = TaskStatus.PENDING
    max_iterations: int = 10
    iteration_count: int = 0
    validation_errors: List[str] = field(default_factory=list)
    
    def add_step(self, step_type: ReasoningStep, content: str, metadata: Optional[Dict[str, Any]] = None):
        """Add a reasoning step."""
        step = {
            "type": step_type.value,
            "content": content,
            "step_number": len(self.steps) + 1,
            "metadata": metadata or {}
        }
        self.steps.append(step)
        logger.debug(f"Added {step_type.value} step: {content[:100]}...")
    
    def add_observation(self, observation: str):
        """Add an observation from tool execution."""
        self.observations.append(observation)
        logger.debug(f"Observation: {observation[:100]}...")
    
    def add_tool_result(self, tool_name: str, result: Any):
        """Add a tool execution result."""
        self.tool_results.append({
            "tool": tool_name,
            "result": result
        })


class TaskValidator(BaseModel):
    """Validator for task outputs."""
    task_type: str
    required_fields: List[str] = Field(default_factory=list)
    validation_rules: Dict[str, Any] = Field(default_factory=dict)  # Store as Any, validate manually
    language_requirement: Optional[str] = None  # e.g., "japanese", "english"
    
    def _get_validator_func(self, field: str) -> Optional[Callable]:
        """Get validator function for a field."""
        validator = self.validation_rules.get(field)
        if callable(validator):
            return validator
        return None
    
    def validate(self, output: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Validate task output.
        
        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []
        
        # Check required fields
        for field in self.required_fields:
            if field not in output or not output[field]:
                errors.append(f"Missing required field: {field}")
        
        # Check validation rules
        for field, validator_func in self.validation_rules.items():
            validator = self._get_validator_func(field)
            if validator and field in output:
                try:
                    if not validator(output[field]):
                        errors.append(f"Validation failed for field: {field}")
                except Exception as e:
                    errors.append(f"Validation error for {field}: {str(e)}")
        
        # Check language requirement
        if self.language_requirement:
            content = output.get("content", "") or str(output)
            if not self._check_language(content, self.language_requirement):
                errors.append(
                    f"Language requirement not met: expected {self.language_requirement}, "
                    f"but content appears to be in a different language"
                )
        
        return len(errors) == 0, errors
    
    def _check_language(self, text: str, expected_lang: str) -> bool:
        """Simple language detection (can be enhanced with proper NLP library)."""
        if expected_lang.lower() == "japanese":
            # Check for Japanese characters (hiragana, katakana, kanji)
            japanese_chars = any(
                '\u3040' <= char <= '\u309F' or  # Hiragana
                '\u30A0' <= char <= '\u30FF' or  # Katakana
                '\u4E00' <= char <= '\u9FAF'     # Kanji
                for char in text
            )
            return japanese_chars
        return True  # For other languages, assume valid for now


# Validators for different task types
RIREKISHO_VALIDATOR = TaskValidator(
    task_type="rirekisho",
    required_fields=[
        "職務要約",
        "活用できる経験・知識・スキル",
        "職務経歴",
        "技術スキル",
        "資格",
        "自己PR",
        "語学力",
        "志望動機"
    ],
    language_requirement="japanese",
    validation_rules={
        "職務要約": lambda x: isinstance(x, str) and 200 <= len(x) <= 500,
        "活用できる経験・知識・スキル": lambda x: isinstance(x, list) and len(x) >= 3,
    }
)

SHOKUMU_KEIREKISHO_VALIDATOR = TaskValidator(
    task_type="shokumu_keirekisho",
    required_fields=[
        "経歴要約",
        "職務内容",
        "活用できる経験・知識・スキル",
        "自己PR"
    ],
    language_requirement="japanese",
    validation_rules={
        "経歴要約": lambda x: isinstance(x, str) and 200 <= len(x) <= 500,
    }
)


def create_reasoning_prompt(state: ReasoningState) -> str:
    """
    Create a reasoning prompt based on current state.
    
    This implements the "think" step of ReAct pattern.
    """
    prompt_parts = []
    
    # Task context
    prompt_parts.append(f"**Task**: {state.task}")
    prompt_parts.append(f"**Goal**: {state.goal}")
    prompt_parts.append(f"**Current Status**: {state.status.value}")
    prompt_parts.append(f"**Iteration**: {state.iteration_count}/{state.max_iterations}")
    
    # Previous steps
    if state.steps:
        prompt_parts.append("\n**Previous Steps:**")
        for step in state.steps[-3:]:  # Last 3 steps
            prompt_parts.append(f"- {step['type'].upper()}: {step['content'][:200]}")
    
    # Observations
    if state.observations:
        prompt_parts.append("\n**Observations:**")
        for obs in state.observations[-3:]:  # Last 3 observations
            prompt_parts.append(f"- {obs[:200]}")
    
    # Tool results summary
    if state.tool_results:
        prompt_parts.append("\n**Tool Results:**")
        for tr in state.tool_results[-2:]:  # Last 2 tool results
            tool_name = tr.get("tool", "unknown")
            result_preview = str(tr.get("result", ""))[:150]
            prompt_parts.append(f"- {tool_name}: {result_preview}...")
    
    # Validation errors
    if state.validation_errors:
        prompt_parts.append("\n**Validation Errors (must fix):**")
        for error in state.validation_errors:
            prompt_parts.append(f"- {error}")
    
    # Reasoning instruction
    if state.status == TaskStatus.PENDING or state.status == TaskStatus.IN_PROGRESS:
        prompt_parts.append("\n**Your Task:**")
        prompt_parts.append("1. THINK: Analyze what needs to be done next")
        prompt_parts.append("2. ACT: Decide which tool(s) to use or what to generate")
        prompt_parts.append("3. OBSERVE: Review the results")
        prompt_parts.append("4. Continue until the task is complete")
        
        if state.validation_errors:
            prompt_parts.append("\n⚠️ **IMPORTANT**: You have validation errors. You MUST fix these before proceeding.")
            prompt_parts.append("Review the errors above and regenerate the content to meet all requirements.")
    
    return "\n".join(prompt_parts)


def create_validation_prompt(output: Dict[str, Any], validator: TaskValidator) -> str:
    """Create a prompt for validating output."""
    prompt_parts = []
    prompt_parts.append(f"**Validating {validator.task_type} output:**")
    prompt_parts.append("\n**Required Fields:**")
    for field in validator.required_fields:
        has_field = field in output and output[field]
        status = "✅" if has_field else "❌"
        prompt_parts.append(f"{status} {field}")
    
    if validator.language_requirement:
        prompt_parts.append(f"\n**Language Requirement**: {validator.language_requirement}")
        prompt_parts.append("All content must be in the specified language.")
    
    prompt_parts.append("\n**Output to Validate:**")
    prompt_parts.append(str(output)[:500])
    
    prompt_parts.append("\n**Validation Instructions:**")
    prompt_parts.append("Check if all required fields are present and complete.")
    prompt_parts.append("Verify language requirements are met.")
    prompt_parts.append("Ensure content quality and completeness.")
    
    return "\n".join(prompt_parts)


def decompose_task(task: str) -> List[str]:
    """
    Decompose a complex task into sub-tasks.
    
    This is a simple decomposition - can be enhanced with LLM-based decomposition.
    """
    task_lower = task.lower()
    
    # Rirekisho generation task
    if "rirekisho" in task_lower or "履歴書" in task:
        return [
            "1. Retrieve resume data using get_resume() tool",
            "2. Extract relevant work experience and skills",
            "3. Generate 職務要約 (Job Summary) in Japanese (200-300 words)",
            "4. Generate 活用できる経験・知識・スキル (3 bullet points in Japanese)",
            "5. Generate 職務経歴 (Work History summary in Japanese)",
            "6. Generate 技術スキル (Technical Skills list in Japanese)",
            "7. Generate 資格 (Qualifications list in Japanese)",
            "8. Generate 自己PR (Self-PR in Japanese)",
            "9. Generate 語学力 (Language Skills in Japanese)",
            "10. Generate 志望動機 (Motivation in Japanese)",
            "11. Validate all sections are complete and in Japanese",
            "12. Format final output"
        ]
    
    # Shokumu-keirekisho generation task
    if "shokumu" in task_lower or "職務経歴書" in task:
        return [
            "1. Retrieve resume data using get_resume() tool",
            "2. Extract detailed work history",
            "3. Generate 経歴要約 (Personal History Summary) in Japanese (200-300 chars)",
            "4. Generate 職務内容 (Detailed Work History in Japanese)",
            "5. Generate 活用できる経験・知識・スキル (Skills in Japanese)",
            "6. Generate 自己PR (Self-PR with STAR method in Japanese)",
            "7. Validate all sections are complete and in Japanese",
            "8. Format final output"
        ]
    
    # Generic task decomposition
    return [
        "1. Understand the task",
        "2. Gather required information",
        "3. Generate response",
        "4. Validate output",
        "5. Complete task"
    ]


def should_continue_reasoning(state: ReasoningState) -> bool:
    """Determine if reasoning loop should continue."""
    if state.status == TaskStatus.COMPLETED:
        return False
    if state.status == TaskStatus.FAILED:
        return False
    if state.iteration_count >= state.max_iterations:
        logger.warning(f"Max iterations reached: {state.max_iterations}")
        return False
    return True


def get_validator_for_task(task: str) -> Optional[TaskValidator]:
    """Get appropriate validator for a task type."""
    task_lower = task.lower()
    
    if "rirekisho" in task_lower or "履歴書" in task:
        return RIREKISHO_VALIDATOR
    
    if "shokumu" in task_lower or "職務経歴書" in task:
        return SHOKUMU_KEIREKISHO_VALIDATOR
    
    return None

