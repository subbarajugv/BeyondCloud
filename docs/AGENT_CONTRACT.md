# Agent Contract (BeyondCloud)

**Version**: 1.0  
**Status**: Active  
**Last Updated**: 2026-01-19

This document defines the formal contracts for the BeyondCloud Agent system.

---

## Agent Architecture

```
User → [Intent] → [Planning] → [Context] → [Action] → [Observation] → [Generation]
                       ↑                                                    │
                       │           [Memory] ←──────────────────────────────┘
                       │                ↓
                       └────────── [Error/Recovery]
                                        ↓
                               [Human-in-Loop] (optional)
```

**Add-ons:**
- RAG Contract (retrieval-augmented generation)

---

## Sub-Contract 1: Intent

**Purpose**: Parse user input into structured goal

### Inputs
| Field | Type | Required |
|-------|------|----------|
| `message` | string | Yes |
| `conversationId` | string | Yes |
| `attachments` | File[] | No |

### Outputs
| Field | Type | Description |
|-------|------|-------------|
| `goal` | string | Clear statement of user's objective |
| `constraints` | string[] | Limitations or requirements |
| `taskType` | enum | 'question', 'action', 'creative', 'analysis' |

### Guarantees
- Always produces a goal (even if just echoing input)
- Constraints extracted from context

### Failures
| Code | Meaning |
|------|---------|
| `INTENT_UNCLEAR` | Cannot determine user intent |
| `INTENT_UNSAFE` | Request violates safety policies |

---

## Sub-Contract 2: Planning

**Purpose**: Break goal into executable steps

### Inputs
| Field | Type | Required |
|-------|------|----------|
| `goal` | string | Yes |
| `constraints` | string[] | No |
| `availableTools` | Tool[] | Yes |

### Outputs
| Field | Type | Description |
|-------|------|-------------|
| `plan` | Step[] | Ordered list of steps |
| `estimatedSteps` | number | Expected iteration count |
| `requiresHumanApproval` | boolean | Has dangerous actions |

```typescript
interface Step {
  id: string;
  description: string;
  toolName: string | null;
  dependsOn: string[];  // Step IDs
}
```

### Guarantees
- Plan uses only available tools
- Circular dependencies prevented
- Max 20 steps (configurable)

### Failures
| Code | Meaning |
|------|---------|
| `NO_VIABLE_PLAN` | Cannot achieve goal with available tools |
| `PLAN_TOO_COMPLEX` | Exceeds step limit |

---

## Sub-Contract 3: Context Assembly

**Purpose**: Gather relevant information for current step

### Inputs
| Field | Type | Required |
|-------|------|----------|
| `currentStep` | Step | Yes |
| `conversationHistory` | Message[] | Yes |
| `memory` | MemoryState | No |
| `maxTokens` | number | Yes |

### Outputs
| Field | Type | Description |
|-------|------|-------------|
| `context` | string | Assembled context for LLM |
| `tokenCount` | number | Actual token count |
| `sources` | Source[] | Where context came from |

### Guarantees
- Context fits within `maxTokens`
- Most relevant info prioritized
- Recency bias for conversation history

### Failures
| Code | Meaning |
|------|---------|
| `CONTEXT_OVERFLOW` | Cannot fit minimum context |
| `MEMORY_UNAVAILABLE` | Memory service down |

---

## Sub-Contract 4: Action

**Purpose**: Execute a tool with given arguments

### Inputs
| Field | Type | Required |
|-------|------|----------|
| `toolName` | string | Yes |
| `arguments` | object | Yes |
| `mode` | enum | 'direct', 'http' (remote) |
| `timeout` | number | No (default 30s) |

### Outputs
| Field | Type | Description |
|-------|------|-------------|
| `result` | any | Tool output |
| `executionTime` | number | Milliseconds |
| `status` | enum | 'success', 'error', 'timeout' |

### Guarantees
- Sandboxed execution
- Timeout enforced
- No side effects on failure

### Failures
| Code | Meaning |
|------|---------|
| `TOOL_NOT_FOUND` | Unknown tool name |
| `INVALID_ARGUMENTS` | Args don't match schema |
| `EXECUTION_TIMEOUT` | Exceeded timeout |
| `EXECUTION_ERROR` | Tool threw error |
| `PERMISSION_DENIED` | Tool requires approval |

---

## Sub-Contract 5: Observation

**Purpose**: Process and summarize tool results

### Inputs
| Field | Type | Required |
|-------|------|----------|
| `rawResult` | any | Yes |
| `toolName` | string | Yes |
| `maxLength` | number | No |

### Outputs
| Field | Type | Description |
|-------|------|-------------|
| `observation` | string | Summarized result |
| `structured` | object | Parsed data |
| `shouldContinue` | boolean | More actions needed |

### Guarantees
- Output fits context window
- Large results truncated with summary
- Errors converted to readable format

### Failures
| Code | Meaning |
|------|---------|
| `PARSE_ERROR` | Cannot parse tool output |
| `OBSERVATION_TOO_LARGE` | Cannot summarize adequately |

---

## Sub-Contract 6: Generation

**Purpose**: Produce response or decide next action

### Inputs
| Field | Type | Required |
|-------|------|----------|
| `context` | string | Yes |
| `tools` | OpenAITool[] | No |
| `generationConfig` | Config | No |

### Outputs
| Field | Type | Description |
|-------|------|-------------|
| `type` | enum | 'message', 'tool_call', 'done' |
| `content` | string | If type=message |
| `toolCalls` | ToolCall[] | If type=tool_call |

### Guarantees
- Valid JSON for tool calls
- Respects stop conditions
- Handles streaming

### Failures
| Code | Meaning |
|------|---------|
| `GENERATION_FAILED` | LLM error |
| `INVALID_TOOL_CALL` | Malformed tool call JSON |
| `MAX_TOKENS_EXCEEDED` | Response too long |

---

## Sub-Contract 7: Human-in-Loop

**Purpose**: Get user approval for sensitive actions

### Inputs
| Field | Type | Required |
|-------|------|----------|
| `action` | Action | Yes |
| `reason` | string | Yes |
| `timeout` | number | No |

### Outputs
| Field | Type | Description |
|-------|------|-------------|
| `decision` | enum | 'approve', 'reject', 'modify' |
| `modifiedAction` | Action | If decision=modify |
| `feedback` | string | User's reason |

### Guarantees
- Agent pauses until user responds
- Timeout results in rejection
- Audit log created

### Failures
| Code | Meaning |
|------|---------|
| `APPROVAL_TIMEOUT` | User didn't respond in time |
| `USER_REJECTED` | User rejected action |

### When Required
| `run_command` | Yes (Safe/Moderate/Dangerous levels) |
| `database_query` | Yes (Read-only allowed, Write blocked) |
| `python_executor` | Yes (Sandboxed, blocked imports) |
| `write_file` | Yes (Sandbox path check) |
| External API | Configurable |

---

## Sub-Contract 8: Memory

**Purpose**: Persist important information across sessions

### Inputs
| Field | Type | Required |
|-------|------|----------|
| `conversationId` | string | Yes |
| `userId` | string | Yes |
| `content` | Message | Yes |

### Outputs
| Field | Type | Description |
|-------|------|-------------|
| `stored` | boolean | Successfully stored |
| `memoryId` | string | Reference ID |
| `relevanceScore` | number | Importance 0-1 |

### Guarantees
- Important facts persisted
- User data isolated
- Retrievable by semantic search

### Failures
| Code | Meaning |
|------|---------|
| `MEMORY_FULL` | User quota exceeded |
| `STORAGE_ERROR` | Database error |

---

## Sub-Contract 9: Error/Recovery

**Purpose**: Handle failures gracefully

### Inputs
| Field | Type | Required |
|-------|------|----------|
| `error` | Error | Yes |
| `context` | AgentState | Yes |
| `retryCount` | number | Yes |

### Outputs
| Field | Type | Description |
|-------|------|-------------|
| `strategy` | enum | 'retry', 'fallback', 'abort', 'ask_user' |
| `modifiedAction` | Action | If strategy=retry |
| `userMessage` | string | If strategy=ask_user |

### Guarantees
- Max 3 retries per action
- Exponential backoff
- Always produces user-friendly message

### Recovery Strategies
| Error Type | Strategy |
|------------|----------|
| Timeout | Retry with longer timeout |
| Rate limit | Wait and retry |
| Tool error | Try alternative tool |
| LLM error | Fallback to simpler model |
| Unknown | Ask user for guidance |

---

## Related Contracts

- [API_OVERVIEW.md](API_OVERVIEW.md) - System architecture and service map
- [CONTRACT.md](CONTRACT.md) - Core protocol and error standards
- [RAG_CONTRACT.md](RAG_CONTRACT.md) - Knowledge base retrieval logic
- [RBAC_CONTRACT.md](RBAC_CONTRACT.md) - Role-based access control

---

## Contract Compliance Checklist

### Agent Contracts
- [ ] Intent contract implemented
- [ ] Planning contract implemented
- [ ] Context assembly contract implemented
- [ ] Action contract implemented
- [ ] Observation contract implemented
- [ ] Generation contract implemented
- [ ] Human-in-loop contract implemented
- [ ] Memory contract implemented
- [ ] Error/recovery contract implemented
