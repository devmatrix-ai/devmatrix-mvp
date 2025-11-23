# Enhanced Anthropic Client - Usage Examples

## MVP Features Implemented

✅ **Multi-model Support** (Haiku/Sonnet/Opus)
✅ **Anthropic's Prompt Caching** (32% cost savings)
✅ **Task-based Model Selection** (auto-selects optimal model)
✅ **Cost Tracking** (per-model, with cache savings analysis)

---

## Quick Start

```python
from src.llm import EnhancedAnthropicClient

# Initialize client
client = EnhancedAnthropicClient(
    use_opus=False,  # MVP: disabled
    cost_optimization=True  # Use Haiku for simple tasks
)
```

---

## Example 1: Generate with Prompt Caching (PRIMARY METHOD)

```python
# This is the main method you'll use for MasterPlan execution

response = await client.generate_with_caching(
    # Task metadata
    task_type="task_execution",  # discovery, masterplan_generation, task_execution, etc.
    complexity="medium",  # low, medium, high, critical

    # Cacheable context (repeated across tasks)
    cacheable_context={
        "system_prompt": "You are an expert Python developer...",
        "discovery_doc": {
            "domain": "User Management",
            "bounded_contexts": ["Auth", "Users"],
            "aggregates": [...],
        },
        "rag_examples": [
            {"task": "Create User model", "code": "class User: ..."},
            {"task": "Create Auth endpoint", "code": "def login(): ..."}
        ],
        "db_schema": {
            "tables": ["users", "roles"],
            "relationships": [...]
        }
    },

    # Variable prompt (unique per task)
    variable_prompt="Create a User API endpoint with CRUD operations and authentication",

    max_tokens=8000,
    temperature=0.7
)

# Response structure
print(response["content"])  # Generated code
print(response["model"])  # Selected model (e.g., claude-haiku-4-5-20251015)
print(response["usage"])  # Token usage with cache stats
print(response["cost_usd"])  # Actual cost in USD
print(response["cost_analysis"])  # Detailed savings analysis
```

---

## Example 2: Simple Generation (No Caching)

```python
# For quick/one-off requests

content = await client.generate_simple(
    prompt="Explain what a MasterPlan is in 2 sentences",
    task_type="documentation",
    complexity="low",
    max_tokens=500
)

print(content)
```

---

## Example 3: Model Selection Preview

```python
# Check which model would be selected

model = client.get_model_for_task(
    task_type="discovery",
    complexity="high"
)
# Returns: "claude-haiku-4-5-20251001" (always Sonnet for discovery)

model = client.get_model_for_task(
    task_type="task_execution",
    complexity="medium"
)
# Returns: "claude-haiku-4-5-20251015" (Haiku for cost optimization)
```

---

## Example 4: Cost Estimation

```python
# Estimate cost before execution

cost_info = client.estimate_cost(
    task_type="task_execution",
    complexity="medium",
    input_tokens=50_000,  # 50K input (includes cacheable context)
    output_tokens=5_000,   # 5K output
    cached_tokens=26_000   # 26K from cache
)

print(f"Model: {cost_info['model']}")
print(f"Cost with cache: ${cost_info['cost_with_cache']:.4f}")
print(f"Cost without cache: ${cost_info['cost_without_cache']:.4f}")
print(f"Savings: ${cost_info['savings']:.4f} ({cost_info['savings_percent']:.1f}%)")
```

---

## Example 5: Cache Performance Stats

```python
# Get cache hit rate and savings

stats = client.get_cache_stats()

print(f"Cache writes: {stats['cache_writes']}")
print(f"Cache reads: {stats['cache_reads']}")
print(f"Hit rate: {stats['hit_rate_percent']:.1f}%")
print(f"Total tokens cached: {stats['total_tokens_cached']}")
```

---

## Model Selection Logic (MVP)

### Discovery Phase
```python
task_type = "discovery"
complexity = "high"
# → Always selects: claude-haiku-4-5-20251001
```

### MasterPlan Generation
```python
task_type = "masterplan_generation"
complexity = "high"
# → Always selects: claude-haiku-4-5-20251001
```

### Task Execution
```python
# Low complexity
task_type = "task_execution"
complexity = "low"
# → Selects: claude-haiku-4-5-20251015 (cost optimization)

# Medium complexity
complexity = "medium"
# → Selects: claude-haiku-4-5-20251015 (cost optimization)

# High complexity
complexity = "high"
# → Selects: claude-haiku-4-5-20251001 (better quality)
```

---

## Prompt Caching Strategy

### What Gets Cached (Automatically)

The client automatically marks these sections for caching:
1. **System Prompt** (~3K tokens) - Repeated across all tasks
2. **Discovery Document** (~8K tokens) - Same for all tasks in project
3. **RAG Examples** (~20K tokens) - Similar for related tasks
4. **Database Schema** (~3K tokens) - Stable within project
5. **Project Structure** (~2K tokens) - Updated occasionally

**Total cacheable:** ~36K tokens
**Cache TTL:** 5 minutes (Anthropic's default)
**Discount:** 90% on cached tokens

### Savings Example

```
Without caching (50 tasks):
- Input: 50 × 50K = 2.5M tokens @ $3/M = $7.50

With caching (50 tasks):
- First task: 50K tokens @ $3/M = $0.15
- Next 49 tasks: 26K cached @ $0.30/M + 24K uncached @ $3/M = $3.61
- Total: $3.76 (vs $7.50 = 50% savings on input)
```

---

## Model Pricing Reference

| Model | Input | Output | Cached Input | Context | Output Limit |
|-------|-------|--------|--------------|---------|--------------|
| **Haiku 4.5** | $1/M | $5/M | $0.10/M | 200K | 64K |
| **Sonnet 4.5** | $3/M | $15/M | $0.30/M | 200K | 64K |
| **Opus 4.1** | $15/M | $75/M | $1.50/M | 200K | 32-64K |

---

## Integration with MasterPlan Services

### Discovery Agent
```python
class DiscoveryAgent:
    def __init__(self):
        self.llm = EnhancedAnthropicClient()

    async def conduct_discovery(self, user_request: str):
        # Always uses Sonnet for discovery
        response = await self.llm.generate_simple(
            prompt=f"Conduct DDD discovery for: {user_request}",
            task_type="discovery",
            complexity="high"
        )
        return parse_discovery(response)
```

### MasterPlan Generator
```python
class MasterPlanService:
    def __init__(self):
        self.llm = EnhancedAnthropicClient()

    async def generate_masterplan(self, discovery, rag_learnings):
        # Always uses Sonnet for masterplan
        response = await self.llm.generate_with_caching(
            task_type="masterplan_generation",
            complexity="high",
            cacheable_context={
                "system_prompt": MASTERPLAN_SYSTEM_PROMPT,
                "discovery_doc": discovery.to_dict(),
                "rag_examples": rag_learnings
            },
            variable_prompt="Generate complete MasterPlan with 50 tasks",
            max_tokens=20_000  # MasterPlan needs more output
        )
        return response["content"]
```

### Task Executor
```python
class TaskExecutor:
    def __init__(self):
        self.llm = EnhancedAnthropicClient(cost_optimization=True)

    async def execute_task(self, task, context):
        # Auto-selects Haiku or Sonnet based on complexity
        response = await self.llm.generate_with_caching(
            task_type="task_execution",
            complexity=task.complexity,  # "low", "medium", "high"
            cacheable_context={
                "system_prompt": TASK_SYSTEM_PROMPT,
                "discovery_doc": context["discovery"],
                "rag_examples": context["rag_examples"],
                "db_schema": context["db_schema"],
                "project_structure": context["structure"]
            },
            variable_prompt=self.build_task_prompt(task, context),
            max_tokens=8_000
        )

        logger.info(
            f"Task {task.task_id} executed with {response['model']}, "
            f"cost: ${response['cost_usd']:.4f}, "
            f"cached: {response['usage']['cache_read_input_tokens']} tokens"
        )

        return response["content"]
```

---

## Monitoring & Metrics

The client automatically records Prometheus metrics:

```python
# Request counters
enhanced_llm_requests_total{model="claude-haiku-4-5", task_type="task_execution", status="success"}

# Duration histogram
enhanced_llm_duration_seconds{model="claude-haiku-4-5", task_type="task_execution"}

# Cost tracking
enhanced_llm_cost_usd{model="claude-haiku-4-5", task_type="task_execution"}

# Token usage
enhanced_llm_tokens_total{model="claude-haiku-4-5", type="input"}
enhanced_llm_tokens_total{model="claude-haiku-4-5", type="output"}

# Cache performance
enhanced_llm_cache_hits_total{model="claude-haiku-4-5"}
enhanced_llm_cached_tokens_total{model="claude-haiku-4-5"}
```

---

## Best Practices

### 1. Always Use Caching for Tasks
```python
# ✅ GOOD: Use caching for repeated context
response = await client.generate_with_caching(
    cacheable_context={...},
    variable_prompt="specific task"
)

# ❌ BAD: No caching wastes money
response = await client.generate_simple(
    prompt="huge context + specific task"
)
```

### 2. Let Model Selector Choose
```python
# ✅ GOOD: Auto-selects optimal model
response = await client.generate_with_caching(
    task_type="task_execution",
    complexity="medium"  # → Selects Haiku (3x cheaper)
)

# ⚠️ OK: Force model only if needed
response = await client.generate_with_caching(
    task_type="task_execution",
    complexity="medium",
    force_model="claude-haiku-4-5-20251001"  # Override
)
```

### 3. Monitor Cache Hit Rate
```python
# Check cache performance regularly
stats = client.get_cache_stats()
if stats['hit_rate_percent'] < 50:
    logger.warning("Low cache hit rate - check cacheable context stability")
```

### 4. Estimate Costs Before Batch Operations
```python
# Estimate cost for 50 tasks
total_cost = 0
for i in range(50):
    cached = 26_000 if i > 0 else 0  # Cache kicks in after first task
    cost_info = client.estimate_cost(
        task_type="task_execution",
        complexity="medium",
        input_tokens=50_000,
        output_tokens=5_000,
        cached_tokens=cached
    )
    total_cost += cost_info["cost_with_cache"]

print(f"Estimated total: ${total_cost:.2f}")
```

---

## Troubleshooting

### Cache Not Working
```python
# Check if cache is actually being used
response = await client.generate_with_caching(...)

if response["usage"]["cache_read_input_tokens"] == 0:
    # First request - cache is being written
    logger.info("Cache WRITE: Creating new cache")
else:
    # Subsequent requests - should read from cache
    logger.info(f"Cache HIT: {response['usage']['cache_read_input_tokens']} tokens")
```

### Unexpected Model Selection
```python
# Debug model selection
model = client.get_model_for_task("task_execution", "medium")
print(f"Selected: {model}")

# Check selector config
config = client.get_model_stats()
print(f"Cost optimization: {config['cost_optimization']}")
print(f"Use Opus: {config['use_opus']}")
```

---

## Migration from Base Client

```python
# OLD (base client)
from src.llm import AnthropicClient

client = AnthropicClient()
response = client.generate(
    messages=[{"role": "user", "content": prompt}],
    system="You are...",
    max_tokens=8000
)

# NEW (enhanced client)
from src.llm import EnhancedAnthropicClient

client = EnhancedAnthropicClient()
response = await client.generate_with_caching(
    task_type="task_execution",
    complexity="medium",
    cacheable_context={
        "system_prompt": "You are...",
        # ... other cacheable sections
    },
    variable_prompt=prompt,
    max_tokens=8000
)
```

---

**Status:** ✅ Ready for MVP implementation
**Cost Target:** $11.88 per 50-task project (with caching)
**Expected Savings:** 32% vs without caching
