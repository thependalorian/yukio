# LangGraph Orchestration for Yukio Agent

## Overview

Yukio now supports LangGraph orchestration for advanced workflow management, state tracking, and conditional routing. This enables:

- **Cyclical reasoning**: Agent can loop back to refine responses
- **State management**: Persistent state across execution steps
- **Conditional routing**: Smart routing based on task type and validation
- **Modular architecture**: Separate files for state, nodes, edges, and graph

## Architecture

### File Structure

```
agent/
├── state.py          # State definitions (AgentState, RirekishoState, ReasoningState)
├── nodes.py          # Node implementations (classify_task, load_resume, agent, validate, revise)
├── edges.py          # Edge logic and conditional routing functions
├── graph.py          # Graph construction and compilation
├── agent.py          # PydanticAI agent (existing, unchanged)
└── api.py            # API endpoints (updated to use graph)
```

### Graph Flow

```
START
  ↓
classify_task (determines task type, needs_resume)
  ↓
[Conditional: should_load_resume?]
  ├─→ load_resume (loads resume data)
  │     ↓
  │   [Conditional: route_after_resume]
  │     ├─→ agent (if successful)
  │     └─→ agent (if failed, continue anyway)
  └─→ agent (skip resume)
        ↓
      [Conditional: should_validate?]
        ├─→ validate (for complex tasks)
        │     ↓
        │   [Conditional: route_after_validation]
        │     ├─→ revise (if errors found)
        │     └─→ END (if valid)
        └─→ END (skip validation)
              ↑
              │
        [Conditional: route_after_revision]
          ├─→ validate (re-validate)
          └─→ END (complete)
```

## State Definitions (`state.py`)

### AgentState

Main state for the agent workflow:

```python
class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], operator.add]  # Accumulated messages
    user_input: str
    session_id: str
    user_id: Optional[str]
    agent_outcome: Optional[Dict[str, Any]]
    tool_calls: Annotated[List[Dict[str, Any]], operator.add]
    tool_results: Annotated[List[Dict[str, Any]], operator.add]
    task_type: Optional[str]  # "language_learning", "career_coaching", "rirekisho_generation"
    needs_resume: bool
    validation_errors: List[str]
    needs_revision: bool
    metadata: Dict[str, Any]
```

### Specialized States

- **RirekishoState**: For rirekisho generation workflow
- **ReasoningState**: For ReAct reasoning loop

## Nodes (`nodes.py`)

### Available Nodes

1. **classify_task_node**: Analyzes user input to determine task type
2. **load_resume_node**: Retrieves resume data from knowledge base
3. **agent_node**: Executes PydanticAI agent with context
4. **validate_output_node**: Validates output against requirements
5. **revise_output_node**: Revises output based on validation errors

## Edges (`edges.py`)

### Conditional Edge Functions

- **should_load_resume**: Routes to load_resume or skip
- **should_validate**: Routes to validate or skip
- **should_revise**: Routes to revise or complete
- **route_after_resume**: Routes after resume loading
- **route_after_validation**: Routes after validation
- **route_after_revision**: Routes after revision

## Graph Construction (`graph.py`)

### Usage

```python
from agent.graph import get_agent_graph
from langchain_core.messages import HumanMessage

# Get graph instance
graph = get_agent_graph()

# Initialize state
initial_state = {
    "user_input": "create rirekisho from my resume",
    "session_id": "session_123",
    "user_id": "george_nekwaya",
    "messages": [HumanMessage(content="create rirekisho from my resume")],
    "task_type": None,
    "needs_resume": True,
    "resume_data": None,
    "agent_outcome": None,
    "tool_calls": [],
    "tool_results": [],
    "validation_errors": [],
    "needs_revision": False,
    "metadata": {}
}

# Execute graph
thread = {"configurable": {"thread_id": "session_123"}}
result = await graph.ainvoke(initial_state, thread)
```

## API Integration

### Environment Variable

Set `USE_LANGGRAPH=true` to enable LangGraph orchestration:

```bash
export USE_LANGGRAPH=true
```

### Automatic Routing

The API automatically:
1. Detects complex tasks (rirekisho generation)
2. Routes to LangGraph if enabled
3. Falls back to ReAct or direct agent if LangGraph unavailable

## Installation

```bash
cd yukio
source .venv/bin/activate
pip install langgraph langchain-core
```

## Benefits

1. **Better Control**: Explicit workflow steps and routing
2. **State Persistence**: State saved after each step
3. **Error Recovery**: Can loop back to fix errors
4. **Modularity**: Easy to add new nodes or modify flow
5. **Debugging**: Clear visibility into execution path

## Example: Rirekisho Generation Flow

1. **classify_task**: Detects "rirekisho_generation" task type
2. **load_resume**: Retrieves George's resume data
3. **agent**: Generates rirekisho sections using PydanticAI agent
4. **validate**: Checks all 8 sections are present and in Japanese
5. **revise**: If validation fails, fixes errors
6. **validate**: Re-validates revised output
7. **END**: Returns complete rirekisho

## Future Enhancements

- Multi-agent workflows (separate agents for different tasks)
- Human-in-the-loop nodes
- Parallel execution of independent nodes
- Advanced state management with checkpoints
- Graph visualization

