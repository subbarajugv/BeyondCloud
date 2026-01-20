# Prompt Library 📝

A centralized repository of prompts, templates, and rules for the BeyondCloud platform.

## Directory Structure

```
prompts/
├── README.md           # This file
├── system/             # System prompts for LLMs
├── rag/                # RAG-specific prompts
├── agent/              # Agent prompts by type
├── grounding/          # Grounding rules and constraints
└── templates/          # Reusable prompt components
```

## Usage

### Loading Prompts in Python
```python
from pathlib import Path

def load_prompt(category: str, name: str) -> str:
    path = Path(__file__).parent / "prompts" / category / f"{name}.md"
    return path.read_text()

# Example
system_prompt = load_prompt("system", "default")
```

### Prompt Naming Convention
- Use lowercase with underscores: `coding_assistant.md`
- Include version if needed: `rag_synthesis_v2.md`
- Use `.md` for documentation, `.txt` for raw prompts

## Categories

### `/system` - System Prompts
Base personality and capability definitions for the LLM.

### `/rag` - RAG Prompts
- Query rewriting prompts
- Synthesis/answer generation prompts
- Citation formatting prompts

### `/agent` - Agent Prompts
- Role-specific prompts (CodingAgent, ResearchAgent)
- Planning prompts
- Reflection prompts

### `/grounding` - Grounding Rules
- Safety guardrails
- Response format constraints
- Domain-specific rules

### `/templates` - Reusable Components
- Common sections (identity, constraints)
- Output format templates
- Few-shot examples
