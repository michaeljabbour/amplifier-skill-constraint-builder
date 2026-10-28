---
name: harness-reference
description: "Complete reference tables for Harness Machine modes, agents, recipes, enums, and anti-patterns"
---

## Reference: The Harness Machine Pipeline

The full harness development workflow:

```
/harness-explore  -->  environment map + feasibility assessment
       |
/harness-spec     -->  harness spec (type, scale, constraints, acceptance criteria)
       |
/harness-plan     -->  implementation plan (tasks or STATE.yaml for factory)
       |
/harness-execute  -->  constraint code (generate/critique/refine per iteration)
       |         ^
       |         | (convergence loop via recipe)
       v         |
/harness-verify   -->  evidence: legal action rate, reward measurements
       |
/harness-finish   -->  packaged artifact (nano-amplifier, bundle, or .harness-machine/)
```

At any point, if something goes wrong: `/harness-debug` (4-phase systematic debugging).

**Two-track UX:**
- **Interactive** — work through modes manually, human judgment at each step
- **Factory** — use `harness-factory-generation.yaml` to autonomously generate across many environments

Both tracks produce the same artifact: a **nano-amplifier**.

---

## Reference: Modes

| Mode | Shortcut | Purpose | Who Does The Work | Tool Permissions Summary |
|------|----------|---------|-------------------|--------------------------|
| Explore | `/harness-explore` | Understand target environment, assess feasibility | environment-analyst agent | read_file: safe, bash: warn, write: BLOCKED |
| Spec | `/harness-spec` | Design the harness (type, scale, constraints, criteria) | spec-writer agent | read_file: safe, bash: warn, write: BLOCKED |
| Plan | `/harness-plan` | Create implementation plan or STATE.yaml for factory | plan-writer agent | read_file: safe, bash: warn, write: BLOCKED |
| Execute | `/harness-execute` | Orchestrate generate/critique/refine pipeline | dispatch agents only | read_file: safe, delegate: safe, recipes: safe, write: BLOCKED |
| Verify | `/harness-verify` | Evidence-based measurement of legal action rate | harness-evaluator agent | read_file: safe, bash: safe, write: warn |
| Finish | `/harness-finish` | Package as nano-amplifier, commit, present options | main agent | read_file: safe, bash: safe, write: warn |
| Debug | `/harness-debug` | Diagnose convergence failures, constraint gaps | main agent | read_file: safe, bash: safe, write: BLOCKED |
| Upgrade | `/harness-upgrade` | Check and apply upgrades to existing harnesses | upgrade-checker + upgrade-planner agents | read_file: safe, bash: safe, write: warn |

**Mode transition graph (allowed_transitions):**

| From | Allowed Next Modes |
|------|--------------------|
| harness-explore | harness-spec, harness-debug |
| harness-spec | harness-plan, harness-explore, harness-debug |
| harness-plan | harness-execute, harness-spec, harness-debug |
| harness-execute | harness-verify, harness-debug, harness-spec, harness-plan |
| harness-verify | harness-finish, harness-debug, harness-execute, harness-spec, harness-plan |
| harness-finish | harness-execute, harness-explore — `allow_clear: true` (only mode that can exit) |
| harness-debug | harness-verify, harness-explore, harness-execute |
| harness-upgrade | harness-verify, harness-finish |

---

## Reference: Agents

| Agent | Role | When to Use | Model Role |
|-------|------|-------------|------------|
| `harness-machine:environment-analyst` | Explores target, maps action space, assesses feasibility | MANDATORY — first step in /harness-explore | research, general |
| `harness-machine:mission-architect` | Creates meaningful name, domain-specific system prompt, README, context docs | After exploration, before spec — delegate naming and documentation | reasoning, general |
| `harness-machine:capability-advisor` | Recommends tier, tools, provider; produces pre-checked capability picker | After mission naming, before spec — delegate tier/tool decisions | reasoning, general |
| `harness-machine:spec-writer` | Produces harness specification from exploration | MANDATORY — after exploration, delegate document creation | reasoning, general |
| `harness-machine:plan-writer` | Creates implementation plan (single or factory) | MANDATORY — after spec is approved, delegate plan creation | reasoning, general |
| `harness-machine:harness-generator` | Generates constraint code + nano-amplifier artifacts | MANDATORY — every generate step in /harness-execute | coding, general |
| `harness-machine:harness-critic` | Reviews harness: coverage gaps, over-constraints, edge cases | MANDATORY — every critique step in /harness-execute | critique, reasoning, general |
| `harness-machine:harness-refiner` | Improves harness from critic feedback (LLM as mutation operator) | MANDATORY — every refine step (when critique says NEEDS CHANGES) | coding, general |
| `harness-machine:harness-evaluator` | Independent measurement: legal action rate, reward | MANDATORY — /harness-verify, assess step in single-iteration | critique, reasoning, general |
| `harness-machine:upgrade-checker` | Reads target config.yaml, compares generated_version to current, reports diff | Use at start of /harness-upgrade or before re-generating an existing harness | reasoning, general |
| `harness-machine:upgrade-planner` | Plans ordered upgrade steps from version diff (read-only, produces plan only) | After upgrade-checker report — delegate upgrade plan creation | reasoning, general |

**Fresh agent per task:** Use `context_depth="none"` for generator/critic/refiner. Clean context = focused attention = quality output.

---

## Reference: Recipes

| Recipe | Pattern Type | When to Use |
|--------|-------------|-------------|
| `harness-machine:recipes/harness-single-iteration.yaml` | Sub-recipe, sequential 4-step pipeline | Invoked by refinement-loop only — not for direct use |
| `harness-machine:recipes/harness-refinement-loop.yaml` | While-loop convergence | When you need the autonomous generate/critique/refine loop |
| `harness-machine:recipes/harness-development-cycle.yaml` | Staged recipe, 3 approval gates | Full interactive cycle: explore → spec → plan → execute → verify → finish |
| `harness-machine:recipes/harness-factory-generation.yaml` | Foreach batch recipe | Batch generation across many environments using STATE.yaml |
| `harness-machine:recipes/check-upgrade.yaml` | Simple sequential recipe | Check an existing harness for version drift — read-only, no changes |
| `harness-machine:recipes/execute-upgrade.yaml` | Staged recipe with approval gate | Plan upgrade (analysis stage) → user approves → apply upgrade (execution stage) |

---

## Reference: harness_type Enum

| Value | Description | Core Function Signature | Average Convergence |
|-------|-------------|------------------------|---------------------|
| `action-filter` | Harness proposes legal moves, LLM ranks them | `propose_action(board: str) -> str` | Fastest — filter pre-computes legal set |
| `action-verifier` | LLM proposes, harness validates, retry if illegal (primary focus) | `is_legal_action(board: str, action: str) -> bool` | ~14.5 iterations |
| `code-as-policy` | Pure code chooses the action, no LLM at inference time ($0 cost) | `propose_action(board: str) -> str` (deterministic) | ~89.4 iterations |

---

## Reference: harness_scale Enum

| Value | Artifact Tier | Description |
|-------|--------------|-------------|
| `nano` | Tier 1: Nano-amplifier (3 files) | Single environment, minimal constraints. Output: behavior.yaml + constraints.py + context.md |
| `single` | Tier 1: Nano-amplifier | One environment with full constraint coverage. Same 3-file output, more complete. |
| `library` | Tier 2: Harness Bundle | Multiple nano-amplifiers composed into a full bundle (LabClaw-style). |
| `factory` | Tier 3: .harness-machine/ | STATE.yaml + recipes + templates. Autonomous generation across many environments. |
| `self-improving` | Tier 3: .harness-machine/ | Meta-constraint boundaries, convergence loop design, self-modification limits. |

**Artifact tier summary:**
- **Tier 1** (nano/single): `my-harness/behavior.yaml`, `constraints.py`, `context.md`
- **Tier 2** (library): Full bundle with `bundle.md`, `behaviors/`, `modules/`, `context/`
- **Tier 3** (factory): `.harness-machine/STATE.yaml`, `build.yaml`, `iteration.yaml`, `harnesses/`

---

## Reference: Anti-Rationalization Table

| Your Excuse | Why It's Wrong | What You MUST Do |
|-------------|----------------|-----------------|
| "The harness looks right, I don't need to measure" | Visual inspection is not evidence. Legal action rate must be measured, not eyeballed. | Run verification. Read the output. THEN claim. |
| "One more refinement iteration will fix it" | Plateau after 10+ flat iterations = search strategy problem, not code problem. | Use /harness-debug to diagnose the plateau before continuing. |
| "I'll skip the critic and go straight to evaluate" | Critic finds issues cheaper than evaluation. Skipping critique wastes compute on broken code. | Always run generate → critique → refine → assess in order. |
| "The constraint is obvious, no spec needed" | Obvious constraints have edge cases. Undocumented constraints can't be reviewed. | Write the spec. Every constraint needs rationale. |
| "I can write the harness directly without generating" | Human-written harnesses don't benefit from the convergence loop. Use the pipeline. | Use /harness-execute and the recipe pipeline. |
| "This environment is too complex to constrain" | If feasibility assessment shows go, the pipeline handles complexity. | Trust the loop. Set harness_scale appropriately. |
| "The factory failed on one environment, something is wrong" | Individual failures are expected. Heavy-tailed distribution — some environments take 60+ iterations. | Check STATE.yaml. Retry failed environments separately. /harness-debug if needed. |
| "The legal action rate is 95%, close enough to ship" | 95% means 5% of agent actions are illegal. Acceptable only if spec says so. | Compare against the acceptance criteria in the spec. Don't lower the bar without updating the spec. |
| "Refinement is oscillating, I should start fresh" | Oscillation often means refiner is undoing critic's fixes. Diagnose first. | Load convergence-debugging skill. Identify oscillation pattern. Fix the feedback loop. |
| "I don't need to update STATE.yaml after generation" | STATE.yaml is the factory's memory. Stale state = lost work = duplicate effort. | Always run update-state step. Never skip. |

---

## Reference: Key Commands

```bash
# Run full interactive cycle
amplifier run "execute harness-machine:recipes/harness-development-cycle.yaml \
  with target_description='your target' output_dir='output/my-harness'"

# Run just the refinement loop (after you have spec + plan)
amplifier run "execute harness-machine:recipes/harness-refinement-loop.yaml \
  with spec_path=output/spec.md plan_path=output/plan.md output_path=output/harness"

# Batch factory generation
amplifier run "execute harness-machine:recipes/harness-factory-generation.yaml \
  with environments=['env1','env2','env3'] \
  state_yaml_path=.harness-machine/STATE.yaml \
  output_dir=.harness-machine/harnesses"

# Check pending approvals (staged recipes)
amplifier run "list pending approvals"

# Approve and resume
amplifier run "approve recipe session <session-id> stage exploration"
amplifier run "resume recipe session <session-id>"
```
