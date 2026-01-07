# ReAct (Reasoning + Acting) Implementation

## Overview

Yukio now implements the ReAct (Reasoning + Acting) pattern for complex tasks that require:
- Multi-step reasoning
- Tool usage
- Output validation
- Iterative refinement

## Architecture

### Components

1. **`reasoning.py`**: Core reasoning infrastructure
   - `ReasoningState`: Tracks reasoning loop state
   - `TaskValidator`: Validates task outputs
   - `create_reasoning_prompt()`: Generates reasoning prompts
   - `decompose_task()`: Breaks complex tasks into sub-tasks

2. **`react_executor.py`**: ReAct execution loop
   - `execute_react_task()`: Main ReAct loop implementation
   - Handles: THINK → ACT → OBSERVE → VALIDATE → repeat

3. **Integration in `api.py`**: 
   - Detects complex tasks (rirekisho generation, etc.)
   - Routes to ReAct executor when needed
   - Streams reasoning steps to frontend

## ReAct Pattern Flow

```
1. THINK: Analyze task, decompose into steps
2. ACT: Execute tools or generate content
3. OBSERVE: Review tool results and generated content
4. VALIDATE: Check if output meets requirements
5. If validation fails → THINK again (fix errors)
6. If validation passes → COMPLETE
```

## Task Detection

Complex tasks that trigger ReAct:
- "create rirekisho"
- "generate rirekisho"
- "create shokumu-keirekisho"
- "generate shokumu-keirekisho"
- Japanese equivalents: "履歴書を作成", "職務経歴書を作成"

## Validation

### Rirekisho Validator

Validates that rirekisho output includes:
- ✅ 職務要約 (Job Summary) - 200-300 words
- ✅ 活用できる経験・知識・スキル (3 bullet points)
- ✅ 職務経歴 (Work History)
- ✅ 技術スキル (Technical Skills)
- ✅ 資格 (Qualifications)
- ✅ 自己PR (Self-PR)
- ✅ 語学力 (Language Skills)
- ✅ 志望動機 (Motivation)
- ✅ All content in Japanese (日本語)

### Shokumu-Keirekisho Validator

Validates that shokumu-keirekisho output includes:
- ✅ 経歴要約 (Personal History Summary) - 200-300 characters
- ✅ 職務内容 (Work History)
- ✅ 活用できる経験・知識・スキル (Skills)
- ✅ 自己PR (Self-PR)
- ✅ All content in Japanese (日本語)

## Usage

### Automatic Detection

When a user asks for rirekisho generation, the system automatically:
1. Detects the complex task
2. Routes to ReAct executor
3. Executes reasoning loop
4. Validates output
5. Streams results

### Manual Usage

```python
from agent.react_executor import execute_react_task

async for result in execute_react_task(
    task="create rirekisho from my resume",
    user_message="Help me create a rirekisho",
    session_id="session_123",
    user_id="george_nekwaya",
    stream=True
):
    if result["type"] == "reasoning_step":
        print(f"Reasoning: {result['content']}")
    elif result["type"] == "validation":
        print(f"Validation: {result['status']}")
    elif result["type"] == "final_output":
        print(f"Output: {result['content']}")
```

## Benefits

1. **Better Quality**: Validation ensures complete, correct output
2. **Self-Correction**: Agent can fix errors iteratively
3. **Transparency**: Reasoning steps are visible
4. **Reliability**: Structured approach reduces failures
5. **Language Compliance**: Validates Japanese output requirement

## Configuration

### Max Iterations

Default: 15 iterations
- Can be adjusted in `ReasoningState.max_iterations`
- Prevents infinite loops

### Validation Rules

Custom validators can be added in `reasoning.py`:

```python
CUSTOM_VALIDATOR = TaskValidator(
    task_type="custom_task",
    required_fields=["field1", "field2"],
    language_requirement="japanese",
    validation_rules={
        "field1": lambda x: len(x) > 100
    }
)
```

## Monitoring

The system logs:
- Reasoning steps
- Tool calls
- Validation results
- Iteration count
- Final status

Check logs for:
```
ReAct iteration 1/15
Added think step: Task decomposed into 12 steps...
Observation: Agent response received...
Validation: ✅ Validation passed!
```

## Future Enhancements

1. **LLM-based Task Decomposition**: Use LLM to break down tasks dynamically
2. **Advanced Language Detection**: Use proper NLP library for language validation
3. **Multi-Agent Coordination**: Multiple agents for different sub-tasks
4. **Confidence Scoring**: Rate output quality before validation
5. **Adaptive Validation**: Adjust validation rules based on task complexity

