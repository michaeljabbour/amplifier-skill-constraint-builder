---
name: convergence-debugging
description: "Diagnosing convergence problems in the harness refinement loop — Thompson sampling mechanics, plateau patterns, and when to intervene"
---

# Convergence Debugging

## The Three Convergence Profiles

From the AutoHarness paper (Lou et al., Google DeepMind, 2026, arXiv:2603.03329v1), harness generation shows three distinct convergence patterns across 145 games:

### Profile 1: Fast Converger (~5 iterations)
**Example:** 2048-v0  
**Characteristics:**
- Action space is small and well-defined
- Legality rules are simple and consistent
- First critique identifies a small number of clear gaps
- Refiner patches them cleanly, evaluator confirms convergence

**What you'll see:** Legal action rate jumps from ~70% to 100% in 2-3 iterations. Assessment JSON shows `converged: "true"` early.

**Diagnostic:** If your environment isn't converging this fast, check whether the action space is actually as simple as you think.

---

### Profile 2: Steady Climber (~19 iterations)
**Example:** FrozenLake-v1  
**Characteristics:**
- Action space has moderate complexity
- Multiple distinct constraint rules required
- Each iteration improves coverage by a meaningful increment
- No plateau — just steady progress

**What you'll see:** Legal action rate climbs steadily (e.g., 40% → 55% → 70% → 85% → 95% → 100%) over 15-25 iterations. The heuristic curve has positive slope throughout.

**Diagnostic:** This is the healthy pattern. If you see it, don't intervene. Let it run.

---

### Profile 3: Plateau-then-Breakthrough (~60 iterations)
**Example:** Chess-v0  
**Characteristics:**
- Action space is large and deeply structured (piece-type rules, turn order, special moves like castling/en passant)
- The easy constraints converge fast; the hard ones require exploration
- Thompson sampling must try multiple branches before finding the right constraint combination
- A long plateau (10-20 iterations of flat heuristic) is followed by a sudden jump when the right branch is found

**What you'll see:** Quick climb to ~80%, then flat for 15-25 iterations, then breakthrough to 100%.

**Diagnostic:** This is the correct behavior for complex environments. It looks like failure but isn't — yet. See patience parameter guidance below.

---

## Thompson Sampling Basics

The refinement loop implements tree search over program space using Thompson sampling. Understanding the mechanics helps diagnose when it's stuck vs. making progress.

### How It Works

1. **Arms** = candidate constraint strategies (e.g., "refine is_legal_action", "refine propose_action", "add new rule", "relax existing rule")
2. **Sampling** = choose which arm to pull based on Beta distribution over historical successes/failures
3. **Update** = after each iteration, update the distribution — successes increase exploitation probability, failures increase exploration

### Exploration vs. Exploitation

**High exploration:** Thompson sampling tries diverse strategies, including ones that look unlikely. Good for escaping local optima.

**High exploitation:** Thompson sampling focuses on strategies that have worked before. Good for squeezing out final percentage points.

**The heuristic weight** controls this balance. In the refinement loop, the weight is implicit — critic feedback quality determines how much each iteration informs the next.

### Arm Selection and the Heuristic

Each iteration's `assessment.legal_action_rate` is the heuristic signal. The loop uses this to weight future iteration choices. If the heuristic is flat, the sampling distribution hasn't updated usefully — either:
1. The critic feedback is too vague to guide the refiner
2. The refiner is undoing fixes from the previous iteration
3. The search has found a local optimum that requires a different approach

---

## Diagnosing Plateaus

### Step 1: Measure the Plateau

How many consecutive iterations have the same (or nearly the same) legal action rate?

```
Iteration 15: 82%
Iteration 16: 82%
Iteration 17: 83%
Iteration 18: 82%
Iteration 19: 82%
```

**Patience parameter:** 15 iterations without improvement triggers plateau diagnosis. Don't intervene before 15 flat iterations.

### Step 2: Check the Critic Feedback

Read the last 3-5 critique outputs. Ask:

**Is the feedback actionable?**
- ✅ "is_legal_action() does not check for en passant captures — add rule for position delta on pawn capture moves"
- ❌ "The constraints could be more comprehensive" (too vague)
- ❌ "Improve edge case handling" (no specific guidance)

If feedback is vague → the critic is not finding specific gaps → the easy gaps are closed, harder ones need different search.

**Recommendation:** Increase the specificity requirement in the critic prompt. Ask it to name the exact action that is incorrectly classified and why.

---

### Step 3: Check for Oscillation

Read the last 5-10 refine step outputs. Compare the changes made:

**Healthy iteration:** Refiner adds new rule or narrows existing one. Does not remove previous fixes.

**Oscillation pattern:**
```
Iteration 20: Refiner adds castling rule → rate jumps to 85%
Iteration 21: Refiner adds en passant rule but accidentally removes castling → rate drops to 81%
Iteration 22: Refiner re-adds castling but removes something else → rate at 83%
```

**Diagnosis:** Oscillation means the refiner is working with incomplete context — it doesn't know which previous fixes should be preserved.

**Fix:** Provide the refiner with a "locked constraints" list — rules that have been verified as correct in previous iterations and should not be modified. This is the refinement decision logic from the paper.

---

### Step 4: Check for Decline

If legal action rate is decreasing:
```
Iteration 30: 88%
Iteration 31: 85%
Iteration 32: 82%
```

**Diagnosis:** The refiner is actively breaking working constraints. Possibly over-constraining (blocking valid actions reduces the legal action rate by making previously-passing test cases fail differently).

**Fix:** Reset to the checkpoint best. The loop's `checkpoint_best: true` ensures the best result so far is always saved. Resume from checkpoint and try a different refinement strategy.

---

## The Refinement Decision Logic Table

From the AutoHarness paper — which function to refine based on the failure mode:

| Failure Mode | is_legal_action() verdict | Actual Action Legality | Refine Which Functions |
|---|---|---|---|
| False positive | Returns True (legal) | Action is illegal | BOTH propose_action() AND is_legal_action() |
| False negative | Returns False (illegal) | Action is legal | ONLY is_legal_action() |
| Hallucinated proposal | Returns True (legal) | Action doesn't exist | ONLY propose_action() |
| Coverage gap | Not tested | Uncovered case | ADD new rule to is_legal_action() |

**Key insight from the paper:** When `is_legal_action()` incorrectly approves an illegal action, the error is in the verifier — but it usually means the proposal function is also poorly calibrated for that edge case. Refine both.

---

## Patience Parameter

**Default:** 15 iterations without improvement triggers plateau diagnosis.

### When to Increase Patience

- Complex environments (Chess-style, large state space)
- High branching factor in the action space
- `harness_type = code-as-policy` (average convergence ~89 iterations, vs ~14 for action-verifier)
- Critic feedback shows many specific issues being found and addressed (healthy progress, just slow)

**Rule of thumb for code-as-policy:** Set patience to 30+. The distribution is heavy-tailed.

### When to Decrease Patience

- Simple environments (2048-style, small action space)
- Feedback is vague and not improving
- You're running in batch factory mode with many environments and want faster fail-fast

**Rule of thumb for simple environments:** Patience of 5-7 is often sufficient.

---

## When to Change Strategy

If plateau diagnosis doesn't resolve after one cycle, consider:

### Option 1: Different harness_type

If `action-verifier` is not converging, try `action-filter`:
- Filter pre-computes the legal action set → no iteration needed for coverage
- Trade-off: requires enumerable action space (not always possible)

### Option 2: Different Constraint Approach

If `is_legal_action()` is oscillating with complex rules, try:
- Breaking the function into sub-validators (one per rule type)
- Adding a debug mode that logs which rule rejected each action
- Starting from a stricter subset and relaxing (conservative → permissive iteration)

### Option 3: Manual Intervention

When to stop and involve a human:
- 60+ iterations with no breakthrough (outlier convergence failure)
- Legal action rate declining despite correct-looking critic feedback
- Oscillation between two states for 20+ iterations
- Critic consistently identifies issues that the refiner fails to address

**Use `/harness-debug` mode** for manual investigation. The debug mode provides 4-phase systematic analysis without the constraint that fixes must be delegated to the pipeline.

---

## Quick Diagnostic Checklist

When the loop looks stuck:

```
□ How many consecutive flat iterations? (< 15 = wait, >= 15 = diagnose)
□ Is critic feedback actionable? (specific actions, specific rules)
□ Is refiner oscillating? (compare last 5 refine outputs)
□ Is rate declining? (check if oscillation = over-correction)
□ What does the last assessment JSON say? (check best_so_far)
□ Is checkpoint_best preserving progress?
□ Should patience increase? (complex environment)
□ Is the environment actually convergeable? (revisit feasibility)
```

If the answer to the last question is "maybe not" — return to `/harness-explore` and re-run the feasibility assessment with more evidence.
