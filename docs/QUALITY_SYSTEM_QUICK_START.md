# Quality System Quick Start Guide

## For Developers: How to Use the Quality System

### Basic Usage (Default - Recommended)

The quality system is **enabled by default**. Just use the council as normal:

```python
from app.services.council.orchestrator import CouncilOrchestrator, CouncilConfig

config = CouncilConfig(
    query="Write a function to detect cycles in a linked list",
    api_keys={"openai": "key", "gemini": "key"},
    # Quality system is enabled by default
)

orchestrator = CouncilOrchestrator()
result = await orchestrator.run(config)

# Result now includes quality validation
print(f"Quality passed: {result.quality_gate_passed}")
```

### Accessing Quality Scores

Quality scores are available in the result metadata:

```python
result = await orchestrator.run(config)

if hasattr(result, 'quality_scores'):
    scores = result.quality_scores
    print(f"Substance: {scores.substance_score}/10")
    print(f"Completeness: {scores.completeness_score}/10")
    print(f"Depth: {scores.depth_score}/10")
    print(f"Accuracy: {scores.accuracy_score}/10")
    print(f"Overall: {scores.overall_score}/10")
```

### Manual Complexity Override

If you know the query complexity, you can override auto-detection:

```python
config = CouncilConfig(
    query="Prove the Riemann Hypothesis",
    query_complexity=5,  # Force Level 5 (Research-Grade)
    api_keys=api_keys
)
```

Complexity Levels:
- **1**: Simple factual (e.g., "What is X?")
- **2**: Explanatory (e.g., "How does X work?")
- **3**: Technical implementation (e.g., "Write a function to do X")
- **4**: Research/Analysis (e.g., "Compare X and Y")
- **5**: Research-grade/Expert (e.g., "Prove X")

### Disable for Simple/Fast Queries

For very simple queries where quality validation is overkill:

```python
config = CouncilConfig(
    query="What is 2+2?",
    enable_quality_directive=False,    # Skip directive injection
    enable_quality_validation=False,   # Skip validation
    api_keys=api_keys
)
```

**When to disable**:
- Simple factual queries (Level 1)
- Time-sensitive requests
- Cost-sensitive requests
- Development/testing

**When to keep enabled**:
- Technical implementations (Level 3+)
- Research queries (Level 4-5)
- Production use cases
- When quality matters more than speed

### Progress Callbacks with Quality Scores

Track quality validation in real-time:

```python
async def progress_callback(event):
    if event.get('agent') == 'Quality Validator':
        if 'scores' in event:
            scores = event['scores']
            print(f"Quality: {scores['overall_score']:.1f}/10")

result = await orchestrator.run(config, progress_callback=progress_callback)
```

---

## For API Developers: Exposing Quality Metrics

### Example API Endpoint

```python
from fastapi import APIRouter, Depends
from app.services.council.orchestrator import CouncilOrchestrator, CouncilConfig

router = APIRouter()

@router.post("/collaborate/with-quality")
async def collaborate_with_quality(
    query: str,
    api_keys: dict = Depends(get_api_keys)
):
    config = CouncilConfig(
        query=query,
        api_keys=api_keys,
        enable_quality_validation=True
    )

    orchestrator = CouncilOrchestrator()
    result = await orchestrator.run(config)

    return {
        "status": result.status,
        "output": result.output,
        "execution_time_ms": result.execution_time_ms,
        "quality_metrics": {
            "substance_score": result.quality_scores.substance_score,
            "completeness_score": result.quality_scores.completeness_score,
            "depth_score": result.quality_scores.depth_score,
            "accuracy_score": result.quality_scores.accuracy_score,
            "overall_score": result.quality_scores.overall_score,
            "quality_gate_passed": result.quality_scores.quality_gate_passed
        } if hasattr(result, 'quality_scores') else None
    }
```

---

## For Frontend Developers: Displaying Quality Scores

### Example React Component

```tsx
interface QualityScores {
  substance_score: number;
  completeness_score: number;
  depth_score: number;
  accuracy_score: number;
  overall_score: number;
  quality_gate_passed: boolean;
}

export function QualityScoreCard({ scores }: { scores: QualityScores }) {
  if (!scores) return null;

  const getScoreColor = (score: number) => {
    if (score >= 9) return "text-green-600";
    if (score >= 7) return "text-yellow-600";
    return "text-red-600";
  };

  return (
    <div className="border rounded-lg p-4 bg-gray-50">
      <h3 className="font-semibold mb-2 flex items-center gap-2">
        Quality Assessment
        {scores.quality_gate_passed ? (
          <span className="text-green-600">✓ Passed</span>
        ) : (
          <span className="text-yellow-600">⚠ Needs Review</span>
        )}
      </h3>

      <div className="space-y-2">
        <ScoreRow label="Substance" score={scores.substance_score} />
        <ScoreRow label="Completeness" score={scores.completeness_score} />
        <ScoreRow label="Depth" score={scores.depth_score} />
        <ScoreRow label="Accuracy" score={scores.accuracy_score} />

        <div className="pt-2 border-t">
          <ScoreRow
            label="Overall"
            score={scores.overall_score}
            className="font-bold"
          />
        </div>
      </div>
    </div>
  );
}

function ScoreRow({
  label,
  score,
  className = ""
}: {
  label: string;
  score: number;
  className?: string;
}) {
  const percentage = (score / 10) * 100;
  const color = score >= 7 ? "bg-green-500" : score >= 5 ? "bg-yellow-500" : "bg-red-500";

  return (
    <div className={className}>
      <div className="flex justify-between text-sm mb-1">
        <span>{label}</span>
        <span className="font-mono">{score.toFixed(1)}/10</span>
      </div>
      <div className="w-full bg-gray-200 rounded-full h-2">
        <div
          className={`h-2 rounded-full transition-all ${color}`}
          style={{ width: `${percentage}%` }}
        />
      </div>
    </div>
  );
}
```

---

## Testing Your Implementation

### 1. Unit Tests

Test individual components:

```python
from app.services.council.query_classifier import classify_query_heuristic
from app.services.council.quality_validator import check_code_quality

# Test classification
level = classify_query_heuristic("Prove convergence of gradient descent")
assert level == 5  # Research-grade

# Test code quality check
response = "def foo(): pass"
passes, issues = check_code_quality(response)
assert not passes  # Should fail due to placeholder
```

### 2. Integration Tests

Run the provided test suite:

```bash
cd backend
export OPENAI_API_KEY="your-key"
python test_quality_system.py
```

### 3. Manual Testing

Test with different query types:

```python
# Level 1: Simple factual
await test_query("What is the capital of France?")

# Level 3: Technical implementation
await test_query("Write a binary search function in Python")

# Level 5: Research-grade
await test_query("Prove the convergence of Adam optimizer")
```

---

## Common Patterns

### Pattern 1: Progressive Enhancement

Start without quality validation, add it later:

```python
# Development
config = CouncilConfig(
    query=query,
    enable_quality_validation=False  # Fast iteration
)

# Production
config = CouncilConfig(
    query=query,
    enable_quality_validation=True   # Ensure quality
)
```

### Pattern 2: Quality-Based Retry

Retry with stronger models if quality fails:

```python
result = await orchestrator.run(config)

if hasattr(result, 'quality_scores') and not result.quality_scores.quality_gate_passed:
    print("Quality check failed, retrying with higher complexity...")
    config.query_complexity = min(config.query_complexity + 1, 5)
    result = await orchestrator.run(config)
```

### Pattern 3: User Feedback Loop

Show quality scores to users, let them request improvements:

```python
result = await orchestrator.run(config)

if result.quality_scores.depth_score < 7:
    # Show user: "Response may lack depth. Regenerate?"
    if user_requests_regeneration:
        config.query_complexity += 1
        result = await orchestrator.run(config)
```

---

## Performance Tips

### 1. Cache Classifications

Cache query complexity classifications for similar queries:

```python
from functools import lru_cache

@lru_cache(maxsize=1000)
def get_cached_complexity(query: str) -> int:
    return classify_query_heuristic(query)
```

### 2. Disable for Bulk Operations

For batch processing, consider disabling validation:

```python
queries = [...]  # 100 queries

for query in queries:
    config = CouncilConfig(
        query=query,
        enable_quality_validation=False  # Disable for speed
    )
    result = await orchestrator.run(config)
```

Then validate a sample:

```python
# Validate 10% of results
sample = random.sample(results, len(results) // 10)
for result in sample:
    validation = await validate_response_quality(...)
```

### 3. Use Heuristic Classification

For cost-sensitive applications:

```python
# In query_classifier.py, modify classify_query to use heuristic by default:
complexity = classify_query_heuristic(query)  # Free, instant
# vs
complexity, _ = await classify_query(query, api_keys, use_llm=True)  # Costs $0.0001
```

---

## Debugging

### Enable Verbose Logging

```python
import logging
logging.basicConfig(level=logging.INFO)

config = CouncilConfig(
    query=query,
    api_keys=api_keys,
    verbose=True  # See detailed logs
)
```

### Check Quality Validation Output

```python
result = await orchestrator.run(config)

if hasattr(result, 'quality_validation_result'):
    validation = result.quality_validation_result
    print(f"Gaps identified: {validation.gaps_identified}")
    print(f"Reasoning: {validation.validation_reasoning}")
```

### Test Individual Components

```python
# Test classification alone
from app.services.council.query_classifier import classify_query
level, reasoning = await classify_query(query, api_keys)
print(f"Level {level}: {reasoning}")

# Test validation alone
from app.services.council.quality_validator import validate_response_quality
validation = await validate_response_quality(query, response, complexity, api_keys)
print(validation.scores.to_dict())
```

---

## FAQ

**Q: Does this slow down responses?**
A: Yes, by 3-6 seconds total (classification + validation). Disable for time-sensitive queries.

**Q: Does this increase costs?**
A: Yes, by <$0.01 per council run. Negligible for most use cases.

**Q: Can I customize the quality criteria?**
A: Yes, edit `QUALITY_VALIDATOR_PROMPT` in `quality_validator.py`.

**Q: Can I add custom quality checks?**
A: Yes, extend `validate_response_quality()` or add heuristics to `analyze_response_heuristics()`.

**Q: What if quality validation fails?**
A: The system appends additional content to fill gaps. If still failing, logs a warning but doesn't block.

**Q: Can I disable quality validation for specific agent types?**
A: Currently no, it's all-or-nothing. You can request this feature.

---

## Migration Guide

### Migrating from Old Council Code

**Before**:
```python
config = CouncilConfig(query=query, api_keys=api_keys)
result = await orchestrator.run(config)
```

**After** (no changes needed - backward compatible):
```python
config = CouncilConfig(query=query, api_keys=api_keys)
result = await orchestrator.run(config)  # Quality system enabled by default
```

**To access new quality metrics**:
```python
if hasattr(result, 'quality_scores'):
    print(f"Quality: {result.quality_scores.overall_score}/10")
```

### Migrating Database Schema

If you persist council results, add quality columns:

```sql
ALTER TABLE collaborate_run ADD COLUMN substance_score FLOAT;
ALTER TABLE collaborate_run ADD COLUMN completeness_score FLOAT;
ALTER TABLE collaborate_run ADD COLUMN depth_score FLOAT;
ALTER TABLE collaborate_run ADD COLUMN accuracy_score FLOAT;
ALTER TABLE collaborate_run ADD COLUMN overall_quality_score FLOAT;
ALTER TABLE collaborate_run ADD COLUMN quality_gate_passed BOOLEAN;
```

---

## Support

For issues or questions:
- Check `QUALITY_SYSTEM_IMPLEMENTATION.md` for detailed architecture
- Run `python test_quality_system.py` to diagnose issues
- Review logs with `verbose=True`
- Check the GitHub issues page

**Happy coding with quality-assured AI responses!** 🚀
