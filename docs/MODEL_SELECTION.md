# Zileas Model Selection Architecture
> Version: 0.1.0 | Date: 2026-02-07

---

## Philosophy

**Local first. API as safety net. User never thinks about model selection.**

Zileas auto-routes queries to the right model tier based on complexity.
The user sees one response. The routing is invisible unless they want to override.

---

## Model Tiers

### Tier 1: Elementary (mistral:7b — 4 GB, always loaded)
**Response time:** < 2 seconds
**When:** Simple queries that don't need heavy reasoning
- Questions under 20 words with no technical terms
- Factual lookups, math, conversions, definitions
- Greetings, small talk, clarifying questions
- "What time is it in Tokyo?"
- "Convert 5km to miles"
- "What does API stand for?"

### Tier 2: High School (llama3.3:70b — 43 GB, load on demand)
**Response time:** 5-10 seconds
**When:** Single-concept explanations, simple code, writing
- "Explain recursion with an example"
- "Write a bash script to rename files"
- "Draft an email to a client about delays"
- "Summarize this article"
- "Compare React vs Vue"

### Tier 3: College (qwen-coder:32b + mistral-large:123b — 93 GB parallel)
**Response time:** 10-20 seconds
**When:** Multi-step problems requiring domain expertise
- "Build a REST API with auth and rate limiting"
- "Debug this Python script" (with code attached)
- "Analyze this CSV and find trends"
- "Write unit tests for this module"
- Code generation with > 50 lines expected output
- Any query containing code blocks or file paths

### Tier 4: Masters (scout + mistral-large + qwen — 160 GB parallel)
**Response time:** 20-40 seconds
**When:** Complex multi-faceted problems
- "Architect a microservices system for..."
- "Review this entire codebase and find issues"
- "Write a PRD for..."
- Input > 2000 tokens
- Queries touching multiple domains (code + business + design)
- "Plan a migration from X to Y"

### Tier 5: PhD (full orchestration + API fallback)
**Response time:** 30-60 seconds
**When:** Highest stakes, local models aren't enough
- Local orchestration confidence < 60% (models disagree)
- Explicit user request (/deep or /api)
- Local model OOM or timeout
- Context exceeds local model limits (> 128K tokens, needs Scout 10M)
- Critical business decisions where wrong answer = real money

---

## API Fallback Providers

| Provider | Model | Use case | Cost |
|----------|-------|----------|------|
| Anthropic | Claude Sonnet 4.5 | General fallback, good at everything | ~$3/M in, $15/M out |
| Anthropic | Claude Opus 4.5 | PhD tier tiebreaker | ~$15/M in, $75/M out |
| OpenAI | GPT-4o | Alternative perspective, good at code | ~$2.50/M in, $10/M out |
| OpenRouter | Any model | Access to specialized models on demand | Varies |
| Google | Gemini 2.5 Pro | Long context (1M+), multimodal | ~$1.25/M in, $10/M out |

### Fallback Priority
1. Try local models first (always)
2. If local fails → Claude Sonnet (best general fallback)
3. If coding specific → GPT-4o (strong at code)
4. If long context needed → Gemini 2.5 Pro
5. If critical/tiebreaker → Claude Opus
6. OpenRouter for anything exotic

### API Trigger Conditions (Automatic)
- Local model crashes (OOM) → auto-fallback to API
- Local model timeout (> 60 seconds) → auto-fallback
- Orchestration confidence < 60% → API as tiebreaker
- Context > 128K tokens → route to Gemini or Scout

### API Trigger Conditions (Manual)
- `/api` command → force next query through API
- `/deep` command → full orchestration + API verification
- Model picker dropdown shows API models alongside local

---

## Router Classification (v1: Rule-Based)

```python
def classify_query(text: str, context: dict) -> str:
    """Classify query into difficulty tier."""
    word_count = len(text.split())
    has_code = bool(re.search(r'```|def |function |class |import ', text))
    has_file_path = bool(re.search(r'[/\\~][\w/\\]+\.\w+', text))
    input_tokens = context.get('total_tokens', 0)
    
    # PhD: explicit request or high-stakes signals
    if '/deep' in text or '/api' in text:
        return 'phd'
    
    # Masters: long input, multi-domain keywords
    if input_tokens > 2000:
        return 'masters'
    if any(w in text.lower() for w in ['architect', 'design system', 'prd',
           'migration plan', 'review codebase', 'full audit']):
        return 'masters'
    
    # College: code-heavy, multi-step
    if has_code or has_file_path:
        return 'college'
    if any(w in text.lower() for w in ['build', 'implement', 'debug',
           'refactor', 'deploy', 'analyze data', 'unit test']):
        return 'college'
    
    # High School: explain, write, summarize
    if any(w in text.lower() for w in ['explain', 'write', 'draft',
           'summarize', 'compare', 'describe', 'how does']):
        return 'high_school'
    
    # Elementary: short, simple
    if word_count < 20:
        return 'elementary'
    
    # Default: High School (safe middle ground)
    return 'high_school'
```

---

## Training Data Collection (v1 → v2 upgrade path)

Every query is logged for future fine-tuning:

```json
{
  "timestamp": "2026-02-07T20:30:00Z",
  "query": "Build a REST API with auth",
  "word_count": 7,
  "has_code": false,
  "router_tier": "college",
  "router_version": "rules_v1",
  "models_used": ["qwen2.5-coder:32b", "mistral-large:123b"],
  "response_time_ms": 14200,
  "user_override": null,
  "user_feedback": "thumbs_up",
  "api_fallback_used": false
}
```

After ~500 logged queries:
1. Export training data
2. Fine-tune llama3.2:1b (1 GB) as classifier
3. Replace rule-based router with fine-tuned model
4. Router adds < 50ms overhead, stays loaded permanently

---

## RAM Budget

```
ALWAYS LOADED (5.7 GB):
  mistral:7b           4.4 GB   (fast tier)
  nomic-embed-text     0.3 GB   (embeddings)
  llama3.2:1b          1.0 GB   (router, after fine-tune)

ON-DEMAND POWER (load as needed):
  llama3.3:70b        43 GB     (high school)
  qwen2.5-coder:32b   20 GB     (college - code)
  mistral-large:123b   73 GB     (college/masters - reasoning)
  llama4:scout         67 GB     (masters - synthesis)
  deepseek-r1:32b      20 GB     (specialist - deep reasoning)

MAX SIMULTANEOUS:
  scout + mistral-large + qwen = 160 GB + 6 GB always = 166 GB
  Leaves 346 GB for OS, apps, buffers ✅

NEVER LOAD:
  llama3.1:405b       243 GB    (replaced by mistral-large)
```

---

## Ollama Model Management

Ollama auto-unloads models after idle timeout (default 5 min).
Zileas should:
1. Pre-load fast tier on startup (mistral:7b + nomic)
2. Load power tier models on-demand when router classifies
3. Keep loaded models warm for 10 min after last use
4. Unload explicitly if RAM needed for a larger model
5. Monitor RAM and refuse to load if would exceed 400 GB total

---

## Open Questions
1. Should we show the user which tier was selected? (subtle badge?)
2. API spend limit per day/month? (safety guardrail)
3. Should the router consider conversation history or just current message?
