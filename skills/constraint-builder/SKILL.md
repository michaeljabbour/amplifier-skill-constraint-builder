---
name: constraint-builder
description: "Turn an action boundary into a testable constraint harness, with legal actions still possible. Use when asked to design, repair or evaluate constraints on agent actions."
---

# Constraint Builder

Start with the action boundary and what a legal action means in the actual environment. Separate soft guidance, enforceable checks and audit policy; do not describe prompt compliance as enforcement.

Explore: read references/constraint-design.md. Identify observable state, allowed actions, irreversible costs and cases the checker cannot decide. Ask one missing question at a time only where it changes the design.

Build: write an explicit action spec and expected legal/illegal examples before tuning. Generate a validator and exercise it through the real dispatch boundary. The packaged scripts/check_actions.py uses the retained Pico gate for trusted local candidate Python; it evaluates supplied actions without dispatching them. Report false rejections as well as illegal escapes. Passing supplied cases is not proof of unseen safety.

Debug: read references/convergence-debugging.md for plateau diagnosis and bounded refinement. Keep generator, critic and evaluator roles separate when measuring improvements. Freeze held-out cases before refinement. Stop when the agreed test/reward bar is met or the budget is exhausted; report a plateau plainly.

The original Pico/Nano/Micro runtimes, hook and factory recipes remain optional repository engines. Use the smallest engine that supplies the actual enforcement boundary. Existing Amplifier modes are adapters to this method.
