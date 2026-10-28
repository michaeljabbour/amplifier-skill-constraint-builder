---
name: constraint-design
description: "How to design good constraints — three layers from the Claw ecosystem, risk assessment, composition patterns, and common mistakes"
---

# Constraint Design

## The Three Constraint Layers

Effective constraint harnesses combine three layers. Each layer has a different enforcement mechanism, cost, and failure mode. Understanding which layer to use — and when to combine them — is the core skill of constraint design.

### Layer 1: Behavioral Constraints (Soft)

**Mechanism:** SKILL.md instructions, context files, prompt-level rules  
**Enforcement:** LLM compliance — the agent reads and follows the rules  
**Cost:** Near-zero. Just text.  
**Failure mode:** LLM ignores or forgets under pressure  
**Claw equivalent:** OpenClaw (skill-based behavioral guidance), LabClaw (206+ domain skills)

Examples:
- "Do not run `rm -rf` on paths outside the project directory"
- "Always call `verify_safety()` before any irreversible operation"
- SKILL.md loaded via `@mentions` in agent context

**What behavioral constraints are good at:**
- Shaping default behavior for well-behaved agents
- Explaining rationale ("why" not just "what")
- Soft guardrails that don't need to be 100% enforced
- Domain knowledge that guides correct action selection

**What they cannot do:**
- Stop a determined agent (or attacker) from violating rules
- Enforce rules that require runtime state (e.g., "only during business hours")
- Provide audit evidence that rules were followed

---

### Layer 2: Enforcement Constraints (Hard)

**Mechanism:** Hook deny/modify, container isolation, OS-level sandboxing  
**Enforcement:** Kernel-level or hook-level — violations are rejected, not just discouraged  
**Cost:** Medium. Requires hook code or container configuration.  
**Failure mode:** Over-blocking (blocking valid actions), or bypassed via unexpected code paths  
**Claw equivalent:** NanoClaw (OS-level container isolation, ~3,900 lines, security-first)

Examples:
- `hook: tool:pre → deny` if action is not in the legal set
- Container filesystem restriction (project directory only)
- `is_legal_action()` returning False → agent must retry
- Hook `modify` to sanitize parameters before execution

**What enforcement constraints are good at:**
- Safety-critical rules that must not be violated
- Rules that can be evaluated deterministically (not ambiguously)
- Providing hard guarantees: "this class of action cannot execute"
- Rejection sampling: let LLM propose, harness validates, retry if illegal

**What they cannot do:**
- Handle subjective rules ("is this response appropriate?")
- Replace behavioral guidance for complex judgment calls
- Explain to the agent WHY an action was rejected (pair with behavioral layer for this)

---

### Layer 3: Policy Constraints (Programmatic)

**Mechanism:** Governance rules, audit trail, compliance frameworks, Colang DSL  
**Enforcement:** Programmatic policy engine — rules are codified and executable  
**Cost:** High. Requires policy specification, testing, and ongoing maintenance.  
**Failure mode:** Policy drift (rules become outdated), incomplete coverage, false positives  
**Claw equivalent:** NemoClaw (NVIDIA enterprise guardrails with Colang DSL)

Examples:
- "No PII in agent outputs" — checked by policy engine on every response
- Audit trail for all tool calls with retention and reporting
- Compliance rule: "data cannot leave EU region" — enforced programmatically
- Multi-layer governance: input moderation + output filtering + action governance

**What policy constraints are good at:**
- Enterprise compliance requirements (GDPR, HIPAA, SOC2)
- Audit evidence and reporting
- Complex conditional rules (role-based, context-dependent)
- Self-improving governance as policy rules evolve

**What they cannot do:**
- Replace hard enforcement for safety-critical actions (pair with Layer 2)
- Handle real-time performance-sensitive contexts (policy engines add latency)

---

## Risk Assessment: When to Use Each Layer

| Scenario | Layer 1 (Behavioral) | Layer 2 (Enforcement) | Layer 3 (Policy) |
|----------|----------------------|-----------------------|------------------|
| Guiding correct tool use | ✅ Primary | Optional | Not needed |
| Preventing filesystem escape | ⚠️ Insufficient alone | ✅ Required | Optional |
| Domain knowledge (lab protocols) | ✅ Primary | Optional for critical steps | Not needed |
| Data exfiltration prevention | ❌ Not sufficient | ✅ Required | ✅ Add for audit |
| Game action legality (AutoHarness) | ✅ Context file | ✅ is_legal_action() hook | Not needed |
| Enterprise compliance | ✅ Policy documentation | ✅ Hard blocks on violations | ✅ Required |
| Developer tool safety (no rm -rf) | ✅ Guidance | ✅ Command allowlist | Optional |
| Content moderation | ⚠️ Insufficient alone | ⚠️ Partial | ✅ Required |

**Quick heuristic:**
- Can a single mistake cause irreversible harm? → Layer 2 required
- Does it need an audit trail? → Layer 3 required  
- Is it guidance for judgment? → Layer 1 sufficient
- All other cases → Layer 1 + Layer 2

---

## How Layers Compose

### Pattern A: Behavioral + Enforcement (Most Common)

The default pattern for harness work. Behavioral layer explains WHY, enforcement layer ensures it regardless.

```
SKILL.md / context.md          ← explains rules, rationale, examples
     +
hook deny/is_legal_action()    ← enforces rules, rejects violations
```

**Works for:** Game harnesses, developer tooling, domain skill constraints, most nano-amplifiers.

### Pattern B: Behavioral Only (Low-risk)

Appropriate only when violation costs are low and you trust the agent.

```
SKILL.md with clear rules       ← agent reads and follows
```

**Works for:** Style guidelines, soft preferences, documentation standards.  
**Not appropriate for:** Security, safety, compliance.

### Pattern C: Behavioral + Enforcement + Policy (Enterprise)

Full three-layer stack. Every action is guided, enforced, and audited.

```
SKILL.md / context.md           ← guidance and rationale
     +
hook deny/modify                ← hard enforcement
     +
policy engine (Colang / audit)  ← compliance and reporting
```

**Works for:** Enterprise deployments, regulated industries, multi-tenant systems, high-stakes automation.

---

## Common Mistakes

### Over-Constraining (Blocking Valid Actions)

**Symptom:** Agent frequently gets rejected for actions that should be legal. Task completion rate drops. Agent enters retry loops.

**Cause:** Constraint rules are too broad or don't account for edge cases in the legal action space.

**Examples:**
- Blocking all `bash` calls when only `rm -rf` is unsafe
- Rejecting moves that are valid but unusual in a game harness
- Allowlist that's missing common legitimate operations

**Fix:** Review the spec's legal action space definition. Narrow your deny rules. Add explicit `allow` conditions for edge cases. Test on a diverse sample of valid actions.

---

### Under-Constraining (Missing Edge Cases)

**Symptom:** High legal action rate in testing, but illegal actions slip through in novel situations. The harness works until it doesn't.

**Cause:** Constraints cover the happy path but miss edge cases in the action space boundary.

**Examples:**
- `is_legal_action()` checks piece type but not whose turn it is
- Path validation checks the prefix but not symlinks/traversal
- Command allowlist misses aliases and shell expansions

**Fix:** Explicitly enumerate edge cases in the spec. Test on boundary conditions. Have the harness-critic review for coverage gaps specifically.

---

### Wrong Layer (Using Behavioral for Safety-Critical)

**Symptom:** The constraint "works" in testing but fails under unusual agent behavior or adversarial prompts.

**Cause:** Relying on LLM compliance (Layer 1) for a rule that requires hard enforcement (Layer 2).

**Examples:**
- "Don't delete files outside the project" as a SKILL.md rule without a hook
- Content guidelines as instructions without output filtering
- "Only propose valid moves" as a prompt without `is_legal_action()` validation

**Fix:** Ask: "What happens if the agent ignores this rule?" If the answer is "bad things," use Layer 2.

---

## The YAGNI Principle Applied to Constraints

Start with the minimum constraints that satisfy your acceptance criteria. Add more only when:
1. Testing reveals a gap (evidence-based)
2. The spec explicitly requires it
3. Risk assessment shows it's needed

**Anti-pattern:** "While I'm here, let me also constrain X because it seems risky." This is over-engineering. Unmeasured constraints become untested constraints become hidden failure modes.

**Rule:** Every constraint must have a corresponding test case. If you can't write a test that fails without the constraint, you don't need it yet.

---

## From the Claw Ecosystem: Layer Examples

| Ecosystem | Layer | Approach | Scale |
|-----------|-------|----------|-------|
| OpenClaw | Behavioral | SKILL.md constraints for agentic coding | Nano to single |
| LabClaw | Behavioral | 206+ composable domain skills for lab automation | Library |
| NanoClaw | Enforcement | OS-level container isolation, ~3,900 lines, security-first | Single to library |
| NemoClaw | Policy | NVIDIA Colang DSL, enterprise guardrails, audit | Enterprise |

The AutoHarness pattern (`action-verifier` with `is_legal_action()`) is a **Layer 2** enforcement constraint. It doesn't rely on the agent being well-behaved — it enforces legality regardless.
