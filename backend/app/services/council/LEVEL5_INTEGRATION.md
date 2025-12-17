# Level 5 Directive Integration Guide

## Overview

The Level 5 directive provides specialized requirements for research-grade queries that require:
- Mathematical proofs or disproofs
- Rigorous derivations from first principles
- Formal analysis with citations
- Experimental validation with complete code

## What's Been Refined

### Original Issues
1. **Verbose and repetitive** - Mixed examples with requirements
2. **Unclear structure** - Hard to distinguish rules from examples
3. **Incomplete guidance** - Missing verification steps
4. **No code examples** - Only described requirements without showing

### Improvements
1. **Clearer sections** - Separated into: Problem Statement → Proof Construction → Citations → Experiments → Verification
2. **Actionable checklists** - Each section has explicit ✓/✗ criteria
3. **Complete examples** - Shows both compliant and non-compliant responses
4. **Runnable code** - Includes full experimental validation template
5. **Better integration** - Designed to work with existing quality_directive.py

## How to Use

### 1. Automatic Application (Recommended)

The directive automatically applies when:
- Query complexity classified as Level 5 (research-grade)
- Query contains proof-related keywords: "prove", "derive", "theorem", etc.

```python
from app.services.council.query_classifier import classify_query
from app.services.council.level5_directive import get_level5_directive, should_apply_level5_directive

# Classify query
complexity, reasoning = await classify_query(user_query, api_keys)

# Apply Level 5 directive if appropriate
if should_apply_level5_directive(user_query, complexity):
    level5_directive = get_level5_directive()
    enhanced_prompt = base_prompt + "\n\n" + level5_directive
```

### 2. Manual Override

For specific cases where you want to force Level 5 rigor:

```python
from app.services.council.level5_directive import get_level5_directive

# Force Level 5 directive regardless of classification
level5_directive = get_level5_directive()
agent_prompt = f"{base_agent_prompt}\n\n{level5_directive}"
```

### 3. Integration with Quality Directive

Update `quality_directive.py` to reference the Level 5 directive:

```python
# In quality_directive.py, update inject_quality_directive function:

def inject_quality_directive(
    agent_prompt: str,
    role: str,
    query_complexity: int = 3,
    include_level5: bool = False  # NEW parameter
) -> str:
    """Inject quality directive into agent prompt."""

    complexity_context = f"""
QUERY COMPLEXITY LEVEL: {query_complexity}/5
{"This is a high-complexity query requiring exceptional depth and rigor." if query_complexity >= 4 else ""}
"""

    role_directive = get_role_specific_directive(role)

    # NEW: Add Level 5 directive if applicable
    level5_addition = ""
    if include_level5 and query_complexity == 5:
        from .level5_directive import get_level5_directive
        level5_addition = f"\n\n{get_level5_directive()}"

    enhanced_prompt = f"""
{QUALITY_DIRECTIVE}

{complexity_context}

{role_directive}

{level5_addition}

=============================================================================
YOUR SPECIFIC ROLE AND INSTRUCTIONS
=============================================================================

{agent_prompt}
"""

    return enhanced_prompt
```

## Key Sections of the Refined Directive

### Section 1: Formal Problem Statement
- How to state claims with mathematical precision
- Defining all symbols and variables
- Identifying proof approach (direct, contradiction, counterexample, induction)

### Section 2: Proof Construction
- Requirements for logical chain of reasoning
- Citation standards for foundational results
- Counterexample construction guidelines
- Explicitly marking where assumptions are used

### Section 3: Citation Standards
- Required format: Author. "Title." Venue Year. [Specific contribution]
- What to cite vs. what not to cite
- Examples of good vs. bad citations

### Section 4: Experimental Validation
- 7-step process: Hypothesis → Setup → Controls → Code → Results → Interpretation → Limitations
- Complete runnable code template (no placeholders)
- How to show and interpret actual numerical results

### Section 5: Verification Checklist
- Proof quality checklist (7 items)
- Citation quality checklist (3 items)
- Code quality checklist (5 items)
- Experimental quality checklist (6 items)
- Overall coherence checklist (5 items)

## Example: Before and After

### Before (Original Directive Fragment)
```
CITATION REQUIREMENTS
---------------------
For research-grade queries, include ACTUAL citations:

Format: Author et al. "Title." Venue Year.  [Key finding relevant to discussion]

Do NOT just mention paper exists — explain what it proves and how it
relates to the current discussion.
```

### After (Refined Directive)
```
=============================================================================
SECTION 3: CITATION STANDARDS FOR RESEARCH-GRADE RESPONSES
=============================================================================

REQUIRED CITATION FORMAT:

Author(s). "Title." Venue Year. [Specific contribution relevant here]

Examples:

✓ "Jacot et al. 'Neural Tangent Kernel: Convergence and Generalization
   in Neural Networks.' NeurIPS 2018. [Introduced NTK framework showing
   infinite-width networks evolve in kernel regime with constant K^∞]"

✗ "Research by Du et al. shows neural networks converge."
   [Too vague — what did they prove? What conditions?]

WHAT TO CITE:
1. FOUNDATIONAL THEOREMS - "Universal Approximation Theorem (Cybenko 1989)..."
2. KEY TECHNICAL RESULTS - "NTK eigenvalue bounds (Allen-Zhu et al. 2019, Theorem 3.2)..."
3. EMPIRICAL BENCHMARKS - "GSM8K accuracy (Wei et al. 2022, Table 2)..."
4. CONTRADICTORY RESULTS - "While Du et al. require m ≥ Ω(n⁶), Oymak 2020 shows..."

WHAT NOT TO CITE:
✗ Common knowledge (backpropagation exists)
✗ Definitions you state yourself
✗ Your own derivations
```

## Testing the Directive

### Test Case 1: Mathematical Proof Query
```
Query: "Prove that gradient descent converges to a global minimum for
overparameterized neural networks."

Expected behavior:
1. Classify as Level 5 (research-grade)
2. Apply Level 5 directive
3. Response should include:
   - Formal problem statement with all notation defined
   - Complete proof with logical steps
   - Citations to Jacot, Du, etc.
   - Runnable code showing NTK stability
   - Actual experimental results
   - Limitations discussion
```

### Test Case 2: Counterexample Query
```
Query: "Disprove the conjecture that all two-layer networks converge
to zero loss with gradient descent."

Expected behavior:
1. Classify as Level 5
2. Response should include:
   - Explicit counterexample construction (dimensions, init, data)
   - Proof that construction satisfies all conditions
   - Proof that loss does NOT converge
   - Code demonstrating the failure
   - Discussion of what this reveals about the theory
```

### Test Case 3: Non-Proof Query (Should NOT Trigger)
```
Query: "Explain how gradient descent works in neural networks."

Expected behavior:
1. Classify as Level 2 (explanatory)
2. Should NOT apply Level 5 directive
3. Response should be clear explanation with examples, ~200-500 words
```

## Metrics for Success

The directive is working well if:

1. **Proof responses include formal statements** - All claims have precise mathematical notation
2. **Citations are substantive** - Each citation explains the specific result, not just name-drops
3. **Code is complete** - Zero placeholders, TODO comments, or undefined functions
4. **Experiments show results** - Not just code, but actual numerical output and interpretation
5. **Depth matches complexity** - Research-grade queries get 2000+ word responses with rigor

## Troubleshooting

### Problem: Agent still producing placeholder code

**Solution**: Check that CREATOR agent is receiving the Level 5 directive. Add explicit validation:

```python
if "# TODO" in response or "pass" in response or "# Placeholder" in response:
    raise ValueError("Level 5 responses must not contain placeholders")
```

### Problem: Citations are still vague

**Solution**: Use the CRITIC agent to validate citation quality:

```python
def validate_citations(response: str) -> bool:
    """Check if citations meet Level 5 standards."""
    citations = extract_citations(response)
    for citation in citations:
        if not has_specific_finding(citation):
            return False
    return True
```

### Problem: Experimental code doesn't run

**Solution**: Add a code execution validator:

```python
def validate_code_runnable(code: str) -> bool:
    """Verify code has no undefined symbols."""
    # Extract all imports
    imports = extract_imports(code)
    # Extract all function calls
    functions = extract_function_calls(code)
    # Verify all called functions are either imported or defined
    return all(is_defined_or_imported(f, code, imports) for f in functions)
```

## Future Enhancements

Potential additions to consider:

1. **Domain-specific directives** - Separate guidance for ML theory vs. algorithms vs. systems
2. **Proof verification** - Automated checking of proof structure and logical flow
3. **Citation database** - Auto-suggest relevant papers based on query topic
4. **Code quality metrics** - Automated scoring of code completeness and clarity
5. **Adaptive depth** - Automatically increase depth if initial response insufficient
