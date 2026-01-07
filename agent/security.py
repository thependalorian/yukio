"""
Security utilities for input validation and prompt injection prevention.

This module provides functions to sanitize user input and prevent
prompt injection attacks that could manipulate the agent's behavior.
"""

import re
import logging
from typing import Optional, List, Tuple

logger = logging.getLogger(__name__)


# Common prompt injection patterns
INJECTION_PATTERNS = [
    # System prompt override attempts
    (r'ignore\s+(previous|all|above)\s+(instructions?|prompts?|rules?)', re.IGNORECASE),
    (r'forget\s+(previous|all|above)\s+(instructions?|prompts?|rules?)', re.IGNORECASE),
    (r'you\s+are\s+now\s+(a|an)\s+', re.IGNORECASE),
    (r'act\s+as\s+(if\s+you\s+are\s+)?(a|an)\s+', re.IGNORECASE),
    (r'pretend\s+(to\s+be|you\s+are)\s+', re.IGNORECASE),
    
    # Instruction manipulation
    (r'new\s+(instructions?|prompts?|rules?|system)\s*:', re.IGNORECASE),
    (r'override\s+(instructions?|prompts?|rules?)', re.IGNORECASE),
    (r'disregard\s+(previous|all|above)', re.IGNORECASE),
    
    # Role hijacking
    (r'you\s+must\s+(now|always|never)', re.IGNORECASE),
    (r'from\s+now\s+on\s+you', re.IGNORECASE),
    (r'your\s+(new|real)\s+(role|job|purpose|identity)', re.IGNORECASE),
    
    # System message injection
    (r'<\|system\|>', re.IGNORECASE),
    (r'<\|assistant\|>', re.IGNORECASE),
    (r'\[SYSTEM\]', re.IGNORECASE),
    (r'\[ASSISTANT\]', re.IGNORECASE),
    
    # Token manipulation
    (r'<\|im_start\|>', re.IGNORECASE),
    (r'<\|im_end\|>', re.IGNORECASE),
    
    # Japanese prompt injection patterns
    (r'以前の(指示|プロンプト|ルール)を(無視|忘れる|破棄)', re.IGNORECASE),
    (r'新しい(指示|プロンプト|ルール)', re.IGNORECASE),
    (r'あなたは(今|これから)(.*?)です', re.IGNORECASE),
]


def detect_prompt_injection(text: str) -> Tuple[bool, List[str]]:
    """
    Detect potential prompt injection attempts in user input.
    
    Args:
        text: User input text to check
        
    Returns:
        Tuple of (is_injection, detected_patterns)
        - is_injection: True if injection patterns detected
        - detected_patterns: List of matched pattern descriptions
    """
    if not text or not isinstance(text, str):
        return False, []
    
    detected = []
    text_lower = text.lower()
    
    for pattern, flags in INJECTION_PATTERNS:
        matches = re.findall(pattern, text, flags)
        if matches:
            pattern_desc = pattern.replace('\\s+', ' ').replace('\\', '')[:50]
            detected.append(f"Pattern: {pattern_desc}")
            logger.warning(f"Potential prompt injection detected: {pattern_desc[:50]}")
    
    # Check for excessive length (potential DoS or injection)
    if len(text) > 10000:
        detected.append("Excessive input length (>10k chars)")
        logger.warning("Input exceeds safe length limit")
    
    # Check for suspicious repetition (potential injection)
    words = text.split()
    if len(words) > 100:
        unique_ratio = len(set(words)) / len(words)
        if unique_ratio < 0.3:  # Less than 30% unique words
            detected.append("Suspicious repetition pattern")
            logger.warning("Input shows suspicious repetition")
    
    is_injection = len(detected) > 0
    return is_injection, detected


def sanitize_input(text: str, max_length: int = 5000) -> str:
    """
    Sanitize user input to prevent prompt injection and ensure safety.
    
    This function:
    1. Truncates excessively long inputs
    2. Removes or escapes dangerous characters
    3. Normalizes whitespace
    4. Preserves Japanese characters and legitimate content
    
    Args:
        text: User input to sanitize
        max_length: Maximum allowed length (default: 5000)
        
    Returns:
        Sanitized text safe for agent processing
    """
    if not text or not isinstance(text, str):
        return ""
    
    # Truncate if too long
    if len(text) > max_length:
        logger.warning(f"Input truncated from {len(text)} to {max_length} characters")
        text = text[:max_length] + "..."
    
    # Remove null bytes and control characters (except newlines and tabs)
    text = re.sub(r'[\x00-\x08\x0b-\x0c\x0e-\x1f\x7f]', '', text)
    
    # Normalize whitespace (preserve single newlines, collapse multiple)
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = re.sub(r'[ \t]+', ' ', text)
    
    # Remove leading/trailing whitespace
    text = text.strip()
    
    return text


def validate_and_sanitize_message(
    message: str,
    check_injection: bool = True,
    max_length: int = 5000
) -> Tuple[str, Optional[str]]:
    """
    Validate and sanitize a user message before processing.
    
    Args:
        message: User message to validate
        check_injection: Whether to check for prompt injection (default: True)
        max_length: Maximum message length (default: 5000)
        
    Returns:
        Tuple of (sanitized_message, error_message)
        - sanitized_message: Cleaned message ready for processing
        - error_message: None if valid, error description if invalid
    """
    if not message:
        return "", "Message cannot be empty"
    
    if not isinstance(message, str):
        return "", "Message must be a string"
    
    # Check for prompt injection
    if check_injection:
        is_injection, patterns = detect_prompt_injection(message)
        if is_injection:
            logger.warning(f"Prompt injection attempt detected: {patterns}")
            # Log but don't block - sanitize instead
            # In production, you might want to block or flag for review
            # For now, we sanitize and continue
    
    # Sanitize the message
    sanitized = sanitize_input(message, max_length=max_length)
    
    if not sanitized:
        return "", "Message is empty after sanitization"
    
    return sanitized, None


def escape_for_prompt(text: str) -> str:
    """
    Escape text to be safely included in a prompt.
    
    This prevents user input from breaking prompt structure.
    
    Args:
        text: Text to escape
        
    Returns:
        Escaped text safe for prompt inclusion
    """
    if not text:
        return ""
    
    # Escape special prompt characters
    # Note: We preserve the text but ensure it's treated as user content
    # The agent's system prompt should handle this, but we add extra safety
    
    # Replace potential prompt markers with escaped versions
    text = text.replace('<|system|>', '&lt;|system|&gt;')
    text = text.replace('<|assistant|>', '&lt;|assistant|&gt;')
    text = text.replace('<|im_start|>', '&lt;|im_start|&gt;')
    text = text.replace('<|im_end|>', '&lt;|im_end|&gt;')
    
    return text

