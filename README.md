# Constraint Builder

Give your agent a boundary it can actually test.

For developers building agent tools. Turn “the agent may do this, but never that” into an action specification, a checker and examples that show whether useful work is still possible.

[Explore the site](https://michaeljabbour.github.io/amplifier-skill-constraint-builder/)

## What you get

- **Catch an escaped action.** Put the check at the dispatch boundary, where an action can be accepted or refused.
- **Keep valid work possible.** Test allowed actions alongside forbidden ones, so a boundary does not win by blocking everything.
- **Know what remains untested.** Keep unseen cases, enforcement limits and the next acceptance test visible.

## Start here

```sh
git clone https://github.com/michaeljabbour/amplifier-skill-constraint-builder.git
cd amplifier-skill-constraint-builder
python3 scripts/capability.py install --dest ~/.agents/skills
```

This installs the portable method and its packaged references into your agent skill folder. If your host uses another folder, pass that path to `--dest`. Start a new session or use your host’s skill refresh so it can discover the installed skill. Optional native tools are installed separately.

Try this first task:

> Use Constraint Builder to specify a file-reading tool that may read project files but may not escape its root. Show legal reads, traversal attempts, symlink cases and false rejections before proposing a checker. Do not execute the proposed actions.

## What you need

- Python 3.11 or later for the portable install helper.
- The portable skill and local checker use Python 3. No model key is needed to install or inspect them.
- The checker evaluates trusted candidate Python locally; it is not an isolation boundary for hostile code.
- The original Pico, Nano, Micro and provider-backed refinement engines are optional.

## Evidence and limits

Local gate and scaffold tests exercise legal actions, illegal actions and failure paths. The provider-backed refinement loop and deployment into a real dispatch boundary require separate acceptance.

The worked examples on the site are fictional. They illustrate the output and decisions; they are not user results or measured benefit. See [consolidation and runtime boundaries](docs/CONSOLIDATION.md) for retained interfaces and acceptance scope.

---

## Retained source guide

### amplifier-bundle-harness-machine

Generate constraint harnesses for LLM agents — from tiny nano-amplifiers to enterprise-scale governance systems. Built on the AutoHarness paper (Lou et al., Google DeepMind, 2026), this bundle provides an eight-mode interactive pipeline and six automation recipes for systematically designing, generating, critiquing, refining, and evaluating constraint harnesses. Whether you're constraining a game-playing agent's action space or building a factory that generates harnesses for dozens of environments, harness-machine gives you the structure to do it rigorously and repeatably.

## Eight-Mode Pipeline

```
  /harness-explore ──► /harness-spec ──► /harness-plan ──► /harness-execute
        │                                                         │
        │                                                         ▼
        │                                                  /harness-verify
        │                                                    │         │
        │                                                    ▼         ▼
        └──────────────────────── /harness-debug ◄── fail  pass ──► /harness-finish

  Existing harness upgrades:
  /harness-upgrade ──► check version ──► plan upgrade ──► (approval) ──► apply upgrade ──► /harness-verify
```

Each mode has a focused role: **explore** maps the environment, **spec** designs the harness, **plan** chooses single vs. factory, **execute** runs the generator/critic/refiner pipeline, **verify** measures legal action rate, **finish** packages and delivers, **debug** handles failures at any stage, **upgrade** checks and applies version upgrades to existing harnesses.

## Two-Track UX

| Track | How | Best For |
|-------|-----|----------|
| **Interactive modes** | `/harness-explore` → `/harness-spec` → `/harness-plan` → `/harness-execute` → `/harness-verify` → `/harness-finish` | Hands-on sessions where you want control and visibility at each step |
| **Factory automation** | `harness-development-cycle.yaml` or `harness-factory-generation.yaml` | End-to-end automation with approval gates; batch generation across environments |

Both tracks produce the same artifact: a constraint harness packaged as a nano-amplifier. Modes give you the steering wheel; recipes give you cruise control.

## Quick Start — Interactive Track

```
# Step 1: Enter explore mode and describe your target environment
/harness-explore

# Step 2: After feasibility assessment, design the harness spec
/harness-spec

# Step 3: Plan implementation (single harness or factory)
/harness-plan

# Step 4: Run the generator → critic → refiner pipeline
/harness-execute

# Step 5: Measure legal action rate and reward
/harness-verify

# Step 6: Package and deliver (merge, PR, or keep)
/harness-finish

# At any point: diagnose constraint failures or convergence plateaus
/harness-debug
```

## Quick Start — Factory Track

```
# Run end-to-end with approval gates between stages
recipes operation=execute recipe_path=@harness-machine:recipes/harness-development-cycle.yaml context={"target_description": "TextArena chess game agent", "output_dir": "output/chess-harness"}

# Batch generation across multiple environments
recipes operation=execute recipe_path=@harness-machine:recipes/harness-factory-generation.yaml context={"environments": ["chess", "poker", "go"], "state_yaml_path": ".harness-machine/STATE.yaml", "output_dir": ".harness-machine/harnesses"}

# Check if an existing harness needs upgrading
recipes operation=execute recipe_path=@harness-machine:recipes/check-upgrade.yaml context={"target_path": "output/chess-harness"}

# Plan and apply an upgrade (staged — requires approval between plan and apply)
recipes operation=execute recipe_path=@harness-machine:recipes/execute-upgrade.yaml context={"target_path": "output/chess-harness"}
```

## Artifact Format

Harness artifacts are delivered in three tiers based on scope:

| Tier | Format | Contents | When to Use |
|------|--------|----------|-------------|
| **Nano** | `.amplifier/` directory | `behavior.yaml`, `constraints.py`, `context.md` | Single environment, single agent |
| **Bundle** | Amplifier bundle | `bundle.md`, `behaviors/`, `modules/` | Reusable harness across projects |
| **Machine** | `.harness-machine/` directory | `STATE.yaml`, recipes, Docker infrastructure | Factory: multiple environments, autonomous loop |

## Available Commands

| Command | Purpose | Next Step |
|---------|---------|-----------|
| `/harness-explore` | Understand environment, map action space, assess feasibility | `/harness-spec` |
| `/harness-spec` | Design harness specification (type, scale, constraints, criteria) | `/harness-plan` |
| `/harness-plan` | Plan implementation: single harness or factory machine | `/harness-execute` |
| `/harness-execute` | Orchestrate generator → critic → refiner pipeline | `/harness-verify` |
| `/harness-verify` | Evidence-based verification: legal action rate, reward measurement | `/harness-finish` or `/harness-debug` |
| `/harness-finish` | Package and deliver: nano-amplifier, bundle, or factory | Session complete |
| `/harness-debug` | Diagnose constraint failures, convergence plateaus, search errors | `/harness-verify` |
| `/harness-upgrade` | Check and apply version upgrades to existing harnesses | `/harness-verify` |

## Decision Architecture: Pico vs Nano vs Micro

The three tiers represent fundamentally different decision-making architectures:

| Tier | Decision Model | Key Capability | Lines |
|---|---|---|---|
| **Pico** | Single-loop reactor | Constraint enforcement + basic tools | 800-1,500 |
| **Nano** | Multi-source reasoner with memory | + streaming, sessions, dynamic context, multi-provider | 2,000-3,500 |
| **Micro** | Orchestrating multi-agent system | + modes, recipes, delegation, approval gates, intent detection | 5,000-8,000 |

**The progression: reactive (pico) → aware (nano) → orchestrating (micro).**

Each tier adds a new dimension of agency, not just more tools. The constraint engine (the safety layer) remains identical across all tiers.

For the full comparison with decision flowcharts, capability matrices, and real-world examples, see **[Decision Architecture Guide](docs/DECISION-ARCHITECTURE.md)**.

## Available Agents

| Agent | Purpose |
|-------|---------|
| `harness-machine:environment-analyst` | Explores target environment, maps action space, scores feasibility |
| `harness-machine:mission-architect` | Creates meaningful name, domain-specific system prompt, README, context docs |
| `harness-machine:capability-advisor` | Recommends tier, tools, provider; produces pre-checked capability picker |
| `harness-machine:spec-writer` | Produces harness specification from exploration results |
| `harness-machine:plan-writer` | Creates implementation plan (single harness or factory machine) |
| `harness-machine:harness-generator` | Generates `is_legal_action()` and `propose_action()` constraint code |
| `harness-machine:harness-critic` | Reviews harness for coverage gaps, over-constraints, and edge cases |
| `harness-machine:harness-refiner` | Improves harness from critic feedback using targeted refinement |
| `harness-machine:harness-evaluator` | Independent measurement of legal action rate and reward signal |
| `harness-machine:upgrade-checker` | Reads target config.yaml, compares version against current, reports diff |
| `harness-machine:upgrade-planner` | Plans ordered upgrade steps from version diff (read-only) |

## Available Recipes

| Recipe | Purpose |
|--------|---------|
| `harness-machine:recipes/harness-single-iteration.yaml` | One generate/critique/refine/evaluate cycle (inner loop) |
| `harness-machine:recipes/harness-refinement-loop.yaml` | Convergence loop with Thompson sampling until target LAR reached |
| `harness-machine:recipes/harness-development-cycle.yaml` | Full cycle with approval gates between explore/spec/plan/execute/verify/finish |
| `harness-machine:recipes/harness-factory-generation.yaml` | Batch generation across multiple environments |
| `harness-machine:recipes/check-upgrade.yaml` | Check existing harness for version drift — read-only, no changes |
| `harness-machine:recipes/execute-upgrade.yaml` | Plan and execute upgrade migration (staged: plan → approve → apply) |

## Skills Library

- **harness-reference** — Complete reference tables: modes, agents, recipes, enums (harness types, scales, convergence strategies)
- **constraint-design** — Three constraint layers (action filtering, reward shaping, state validation), composition patterns, common mistakes
- **convergence-debugging** — Thompson sampling mechanics, plateau detection, search diagnostics, refinement decision logic

```
load_skill(search="harness")
load_skill(skill_name="constraint-design")
load_skill(skill_name="convergence-debugging")
```

## Prerequisites

- [Amplifier](https://github.com/microsoft/amplifier) installed and configured
- [amplifier-foundation](https://github.com/microsoft/amplifier-foundation) bundle (auto-installed via `includes`)

## Installation

```bash
amplifier bundle install git+https://github.com/YOUR_ORG/amplifier-bundle-autoharness@main
```

Or clone and install locally:

```bash
git clone https://github.com/YOUR_ORG/amplifier-bundle-autoharness
amplifier bundle install ./amplifier-bundle-autoharness
```

## Research Foundation

This bundle implements the constraint harness methodology from **AutoHarness: Automated Harness Synthesis Using LLMs** (Lou et al., Google DeepMind, 2026, arXiv:2603.03329). The paper introduces a generate/critique/refine loop for synthesizing `is_legal_action()` and `propose_action()` functions, Thompson sampling for convergence, and a three-tier harness architecture (nano-amplifier → harness bundle → harness machine). The AutoHarness framework achieves high legal action rates across diverse environments by treating constraint generation as an iterative refinement problem with measurable acceptance criteria rather than a one-shot synthesis task.

## License

MIT
