"""
Level 5 (Research-Grade) Query Additional Directive

This module contains specialized requirements for research-grade queries
including mathematical proofs, rigorous derivations, and formal analysis.
"""

LEVEL5_MATHEMATICAL_PROOF_DIRECTIVE = """
=============================================================================
LEVEL 5 ADDITIONAL DIRECTIVE: MATHEMATICAL PROOFS & FORMAL ANALYSIS
=============================================================================

This directive applies when queries explicitly request:
- Proving/disproving conjectures or theorems
- Deriving results from first principles
- Establishing formal convergence properties
- Demonstrating necessary/sufficient conditions

=============================================================================
SECTION 1: FORMAL PROBLEM STATEMENT
=============================================================================

BEFORE attempting a proof, you MUST:

1. STATE THE CLAIM FORMALLY
   ✓ Use precise mathematical notation (ℝ, ∇, ∈, ∀, ∃, etc.)
   ✓ Define ALL symbols, functions, and variables explicitly
   ✓ State ALL assumptions and conditions
   ✓ Clarify the domain and codomain of functions

   Example:
   "Claim: Let f: ℝᵈ → ℝ be a two-layer ReLU network

       f(x; θ) = (1/√m) Σⱼ₌₁ᵐ aⱼ σ(wⱼᵀx + bⱼ)

   where σ(z) = max(0, z), θ = {(wⱼ, bⱼ, aⱼ)}ⱼ₌₁ᵐ, and training uses
   gradient flow dθ/dt = -∇L(θ) with L(θ) = ½ Σᵢ₌₁ⁿ (f(xᵢ; θ) - yᵢ)².

   Then: If m ≥ Ω(n⁶/λ₀⁴) where λ₀ = λₘᵢₙ(K⁽⁰⁾) and K⁽⁰⁾ is the
   initial NTK Gram matrix, then L(θ(t)) → 0 exponentially."

2. IDENTIFY THE APPROACH
   ✓ Direct proof (constructive or non-constructive)
   ✓ Proof by contradiction
   ✓ Proof by counterexample
   ✓ Induction (strong or weak)

   State your strategy explicitly:
   "Approach: We will prove by showing (1) the NTK remains approximately
   constant, (2) this implies convex optimization in function space,
   (3) convergence follows from positive definiteness of K."

=============================================================================
SECTION 2: PROOF CONSTRUCTION REQUIREMENTS
=============================================================================

FOR DIRECT PROOFS:

1. PROVIDE COMPLETE LOGICAL CHAIN
   Each step must follow deductively from:
   - Previous steps
   - Stated assumptions
   - Established theorems (with citations)

   ✓ "From Assumption A and Lemma B, we have X."
   ✗ "It can be shown that X."  [Too vague — show it!]

2. CITE FOUNDATIONAL RESULTS
   When using non-trivial theorems, cite properly:

   Format: Author(s) Year, Key Result

   Example:
   "By the Neural Tangent Kernel theory (Jacot et al. 2018), in the
   infinite-width limit, K⁽ᵗ⁾ = ⟨∇θf(·; θ⁽ᵗ⁾), ∇θf(·; θ⁽ᵗ⁾)⟩ → K^∞
   and remains constant during training. Du et al. 2019 extended this
   to finite width, showing ||K⁽ᵗ⁾ - K⁽⁰⁾|| ≤ ε when m ≥ poly(n, 1/ε)."

3. HIGHLIGHT KEY INSIGHTS
   Don't just compute — explain why each step matters:

   ✓ "The key insight: once K⁽ᵗ⁾ ≈ K⁽⁰⁾, the training dynamics reduce
      to linear regression in the RKHS, guaranteeing convergence if
      λₘᵢₙ(K⁽⁰⁾) > 0."

   ✗ "Therefore K⁽ᵗ⁾ ≈ K⁽⁰⁾."  [States fact without insight]

4. STATE WHERE ASSUMPTIONS ARE USED
   Explicitly flag when assumptions are invoked:

   "Here we critically use the assumption m ≥ Ω(n⁶/λ₀⁴). Without
   sufficient overparameterization, the NTK may change significantly
   during training, invalidating the kernel regime analysis."

FOR COUNTEREXAMPLES:

1. PROVIDE EXPLICIT CONSTRUCTION
   ✓ Specify exact dimensions (d, m, n)
   ✓ Specify initialization (e.g., "wⱼ ~ N(0, I), aⱼ = ±1 uniformly")
   ✓ Specify data distribution (e.g., "xᵢ uniformly on unit sphere")
   ✓ Include numerical values if relevant

   Example:
   "Counterexample construction:
   - Dimension d = 2, width m = 5, samples n = 10
   - Data: xᵢ = eᵢ (standard basis) for i=1,...,d, rest random
   - Labels: yᵢ = 1 for i ≤ d, yᵢ = -1 otherwise
   - Initialization: wⱼ ~ N(0, 0.01·I), aⱼ ~ Unif({-1,1})"

2. PROVE IT SATISFIES THE CLAIM'S CONDITIONS
   Show your counterexample meets all stated assumptions:

   "Verification:
   ✓ Network is two-layer ReLU: f(x;θ) = (1/√5) Σⱼ aⱼ σ(wⱼᵀx)  [by construction]
   ✓ Training uses gradient flow: dθ/dt = -∇L(θ)  [by construction]
   ✓ Data is well-posed: rank({xᵢ}) = d  [standard basis spans ℝᵈ]"

3. PROVE THE FAILURE MODE
   Demonstrate the claim's conclusion fails:

   "Failure demonstration:
   After T = 10⁶ gradient steps with η = 0.01, we observe:
   - Training loss: L(θ(T)) = 0.42 (not converging to 0)
   - NTK drift: ||K⁽ᵀ⁾ - K⁽⁰⁾||_F = 2.1 (violates kernel regime)
   - Minimum eigenvalue: λₘᵢₙ(K⁽ᵀ⁾) = 0.03 << λₘᵢₙ(K⁽⁰⁾) = 1.2

   This violates the claim's conclusion that L → 0."

4. VERIFY NO ASSUMPTION VIOLATIONS
   Ensure you didn't accidentally violate stated conditions:

   "Assumption check:
   The claim requires m ≥ Ω(n⁶/λ₀⁴). In our construction:
   - n = 10, so n⁶ = 10⁶
   - λ₀ ≈ 1.2, so λ₀⁴ ≈ 2.07
   - Required: m ≥ C·(10⁶/2.07) ≈ 483,000 for some constant C
   - Actual: m = 5

   Our counterexample has m << required, so it does NOT violate
   the stated conditions — it shows the bound is tight."

=============================================================================
SECTION 3: CITATION STANDARDS FOR RESEARCH-GRADE RESPONSES
=============================================================================

REQUIRED CITATION FORMAT:

Author(s). "Title." Venue Year. [Specific contribution relevant here]

Examples:

✓ "Jacot et al. 'Neural Tangent Kernel: Convergence and Generalization
   in Neural Networks.' NeurIPS 2018. [Introduced NTK framework showing
   infinite-width networks evolve in kernel regime with constant K^∞]"

✓ "Du et al. 'Gradient Descent Finds Global Minima of Deep Neural Networks.'
   ICML 2019. [Extended NTK to finite width, proved m ≥ Ω(n⁶/λ₀⁴) suffices
   for convergence at rate (1 - ηλ₀)ᵗ]"

✗ "Research by Du et al. shows neural networks converge."
   [Too vague — what did they prove? What conditions?]

✗ "See Jacot et al. for more on NTK."
   [Lazy citation — explain their result]

WHAT TO CITE:

1. FOUNDATIONAL THEOREMS
   "By the Universal Approximation Theorem (Cybenko 1989; Hornik et al. 1989),
   a single hidden layer network can approximate any continuous function..."

2. KEY TECHNICAL RESULTS
   "The NTK eigenvalue λₘᵢₙ is lower bounded by the data separability
   (Allen-Zhu et al. 2019, Theorem 3.2): λₘᵢₙ(K) ≥ κ²/d where κ is
   the minimum pairwise distance between data points."

3. EMPIRICAL BENCHMARKS
   "On GSM8K mathematical reasoning, Chain-of-Thought prompting achieves
   58.1% accuracy vs 17.9% for direct prompting (Wei et al. 2022, Table 2)."

4. CONTRADICTORY RESULTS
   "While Du et al. 2019 require polynomial overparameterization m ≥ Ω(n⁶),
   later work by Oymak & Soltanolkotabi 2020 shows m ≥ O(n log n) suffices
   under stronger assumptions on data distribution."

WHAT NOT TO CITE:

✗ Common knowledge (e.g., "Neural networks use backpropagation")
✗ Definitions you state yourself
✗ Your own derivations (unless building on prior work)

=============================================================================
SECTION 4: EXPERIMENTAL VALIDATION REQUIREMENTS
=============================================================================

When providing empirical validation, follow this structure:

1. HYPOTHESIS STATEMENT
   "Hypothesis: We expect the NTK to remain approximately constant
   (||K⁽ᵗ⁾ - K⁽⁰⁾||/||K⁽⁰⁾|| < 0.1) throughout training when m ≥ 100n,
   but to drift significantly when m < 10n."

2. EXPERIMENTAL SETUP
   Justify all design choices:

   "Setup:
   - Architecture: f(x;θ) = (1/√m) Σⱼ aⱼ ReLU(wⱼᵀx), d=10 input dims
   - Width: m ∈ {50, 100, 500, 1000, 5000} (spanning 5n to 500n)
   - Dataset: n=100 samples from N(0,I), binary labels ±1
   - Training: Full-batch GD with η=0.01, T=5000 steps
   - Init: Xavier for weights (variance 1/d), uniform ±1 for aⱼ
   - Metric: Relative NTK drift ||K⁽ᵗ⁾ - K⁽⁰⁾||_F / ||K⁽⁰⁾||_F

   Rationale: Xavier init ensures O(1) activations; η=0.01 chosen to
   ensure stable convergence; T=5000 sufficient to reach plateau."

3. CONTROLS AND BASELINES
   "Controls:
   - Baseline 1: Random features (frozen weights) — expect no learning
   - Baseline 2: Linear model — expect fast convergence but underfitting
   - Ablation: Test both tanh and ReLU activations"

4. COMPLETE, RUNNABLE CODE
   NO placeholders, NO `pass`, NO `# TODO`:

   ```python
   import torch
   import torch.nn as nn
   import matplotlib.pyplot as plt

   class TwoLayerNet(nn.Module):
       def __init__(self, d, m):
           super().__init__()
           self.fc1 = nn.Linear(d, m, bias=False)
           self.fc2 = nn.Linear(m, 1, bias=False)
           # Xavier init
           nn.init.xavier_normal_(self.fc1.weight)
           # ±1 initialization for second layer
           self.fc2.weight.data = torch.randint(0, 2, (1, m)).float() * 2 - 1
           self.fc2.weight.data /= m**0.5
           # Freeze second layer (NTK regime assumption)
           self.fc2.weight.requires_grad = False

       def forward(self, x):
           return self.fc2(torch.relu(self.fc1(x)))

   def compute_ntk(model, X):
       """Compute empirical NTK K[i,j] = ⟨∇f(xᵢ), ∇f(xⱼ)⟩"""
       n = X.shape[0]
       K = torch.zeros(n, n)
       for i in range(n):
           model.zero_grad()
           out_i = model(X[i:i+1])
           out_i.backward()
           grad_i = torch.cat([p.grad.flatten() for p in model.parameters()
                              if p.requires_grad])
           for j in range(i, n):
               model.zero_grad()
               out_j = model(X[j:j+1])
               out_j.backward()
               grad_j = torch.cat([p.grad.flatten() for p in model.parameters()
                                  if p.requires_grad])
               K[i,j] = K[j,i] = torch.dot(grad_i, grad_j).item()
       return K

   # Experiment
   d, n = 10, 100
   X = torch.randn(n, d)
   y = (torch.randn(n, 1) > 0).float() * 2 - 1

   results = {}
   for m in [50, 100, 500, 1000, 5000]:
       model = TwoLayerNet(d, m)
       K_0 = compute_ntk(model, X)
       K_0_norm = torch.norm(K_0, 'fro').item()

       optimizer = torch.optim.SGD(model.parameters(), lr=0.01)
       ntk_drifts = []

       for t in range(5000):
           optimizer.zero_grad()
           loss = 0.5 * ((model(X) - y)**2).mean()
           loss.backward()
           optimizer.step()

           if t % 500 == 0:
               K_t = compute_ntk(model, X)
               drift = torch.norm(K_t - K_0, 'fro').item() / K_0_norm
               ntk_drifts.append((t, drift))

       results[m] = ntk_drifts

   # Visualization
   plt.figure(figsize=(10, 6))
   for m, drifts in results.items():
       steps, values = zip(*drifts)
       plt.plot(steps, values, label=f'm={m} ({m/n:.1f}n)', marker='o')
   plt.axhline(0.1, color='red', linestyle='--', label='10% drift threshold')
   plt.xlabel('Training Step')
   plt.ylabel('Relative NTK Drift ||K⁽ᵗ⁾ - K⁽⁰⁾|| / ||K⁽⁰⁾||')
   plt.title('NTK Stability vs. Overparameterization')
   plt.legend()
   plt.grid(True)
   plt.savefig('ntk_drift_analysis.png', dpi=150, bbox_inches='tight')
   plt.show()
   ```

5. ACTUAL RESULTS (NOT JUST CODE)
   Don't just provide code — run it and show output:

   "Results:

   Width m    m/n ratio    Final NTK drift    Final loss
   -------    ---------    ---------------    ----------
   50         0.5          0.42               0.31
   100        1.0          0.28               0.18
   500        5.0          0.08               0.03
   1000       10.0         0.04               0.01
   5000       50.0         0.01               0.002

   Observations:
   - NTK drift decreases as m/n increases, confirming theory
   - For m ≥ 10n, drift stays below 10% threshold
   - Convergence improves dramatically with overparameterization
   - Even m = 0.5n shows partial convergence (theory predicts failure)"

6. INTERPRETATION
   Connect results back to the theoretical claim:

   "Interpretation:
   These results support Du et al.'s theoretical prediction that
   sufficient overparameterization (m >> n) keeps the NTK stable.
   However, the required ratio m/n ≈ 10 is far smaller than the
   theoretical bound m ≥ Ω(n⁶), suggesting the bound is pessimistic.

   The linear relationship between log(drift) and log(m/n) suggests
   a power-law: drift ≈ (n/m)^α with α ≈ 0.8."

7. LIMITATIONS
   What does this experiment NOT prove?

   "Limitations:
   - Small scale (n=100, d=10) — results may not generalize to n=10⁶
   - Synthetic data — real datasets have complex structure
   - No generalization analysis — only training dynamics studied
   - Fixed learning rate — adaptive methods (Adam) may behave differently
   - Does not prove convergence, only observes it empirically"

=============================================================================
SECTION 5: FINAL VERIFICATION CHECKLIST
=============================================================================

Before finalizing a Level 5 response, verify ALL of:

PROOF QUALITY:
□ Claim stated with full mathematical rigor (all symbols defined)
□ Proof strategy clearly outlined before diving into details
□ Each step follows logically with explicit justification
□ Key theorems cited with paper references and specific results
□ Assumptions explicitly stated where they're invoked
□ Counterexamples (if provided) include explicit constructions
□ Counterexamples proven to satisfy conditions and fail conclusion

CITATION QUALITY:
□ Minimum 10 specific citations for foundational results
□ Each citation includes: Author, Title, Venue, Year, Key Finding
□ Citations explain HOW the result is relevant, not just that it exists
□ Contradictory results acknowledged if they exist

CODE QUALITY (if applicable):
□ Complete, runnable code (no placeholders, pass, TODO)
□ All imports included
□ No undefined functions or variables
□ Experiments actually test the theoretical claim
□ Code includes comments explaining non-obvious steps

EXPERIMENTAL QUALITY (if applicable):
□ Clear hypothesis stated upfront
□ Experimental setup fully specified with justifications
□ Baseline comparisons or controls included
□ ACTUAL numerical results shown (not just code)
□ Results interpreted in context of original claim
□ Limitations explicitly acknowledged

OVERALL COHERENCE:
□ Response answers the original question completely
□ Depth appropriate for research-grade query (2000+ words)
□ Mathematical notation used correctly and consistently
□ Logical flow from problem → theory → proof → validation → conclusion
□ Honest about what has/hasn't been proven

=============================================================================
EXAMPLES OF COMPLIANT VS. NON-COMPLIANT RESPONSES
=============================================================================

NON-COMPLIANT EXAMPLE:
❌ "To prove neural network convergence, we use the NTK framework.
    The NTK shows that wide networks behave like kernel methods.
    Therefore, they converge to global minima. See Jacot et al. 2018."

Issues:
- No formal problem statement (what claim exactly?)
- No definitions (what is "wide"? what is NTK precisely?)
- No proof steps (just assertion)
- Lazy citation (doesn't explain what Jacot proved)
- No experimental validation
- ~50 words (far below 2000+ requirement)

COMPLIANT EXAMPLE:
✓ "Claim: For a two-layer ReLU network f(x;θ) = (1/√m) Σⱼ aⱼσ(wⱼᵀx)
   trained via gradient flow dθ/dt = -∇L on n samples with squared loss
   L = ½Σᵢ(f(xᵢ;θ) - yᵢ)², if m ≥ Ω(n⁶/λ₀⁴) where λ₀ = λₘᵢₙ(K⁽⁰⁾),
   then L(θ(t)) ≤ L(0)·exp(-ηλ₀t/2).

   Definitions:
   - σ(z) = max(0,z) is ReLU activation
   - θ = {(wⱼ, aⱼ)}ⱼ₌₁ᵐ are parameters
   - K⁽ᵗ⁾[i,j] = ⟨∇θf(xᵢ;θ⁽ᵗ⁾), ∇θf(xⱼ;θ⁽ᵗ⁾)⟩ is the NTK Gram matrix
   - λ₀ = λₘᵢₙ(K⁽⁰⁾) is the minimum eigenvalue at initialization

   Proof strategy:
   (1) Show K⁽ᵗ⁾ ≈ K⁽⁰⁾ for all t when m is large (NTK stability)
   (2) Use kernel stability to reduce dynamics to linear system
   (3) Apply eigenvalue bounds to prove exponential convergence

   Step 1: NTK Stability
   [Detailed proof using Jacot et al. 2018's infinite-width limit
   and Du et al. 2019's finite-width extension...]

   [... continues with complete proof, citations, code, experiments,
   results, interpretation, limitations — total 2500 words]"

=============================================================================
END OF LEVEL 5 DIRECTIVE
=============================================================================
"""


def get_level5_directive() -> str:
    """
    Get the Level 5 additional directive for research-grade queries.

    Returns:
        The complete Level 5 directive text
    """
    return LEVEL5_MATHEMATICAL_PROOF_DIRECTIVE


def should_apply_level5_directive(query: str, complexity_level: int) -> bool:
    """
    Determine if Level 5 directive should be applied.

    Args:
        query: The user's query
        complexity_level: Classified complexity level (1-5)

    Returns:
        True if Level 5 directive should be applied
    """
    if complexity_level != 5:
        return False

    # Additional heuristics for when to apply the rigorous math directive
    level5_keywords = [
        "prove", "disprove", "theorem", "lemma", "derive", "derivation",
        "formal proof", "show that", "demonstrate that", "necessary and sufficient",
        "rigorous", "convergence properties", "from first principles"
    ]

    query_lower = query.lower()
    return any(keyword in query_lower for keyword in level5_keywords)
