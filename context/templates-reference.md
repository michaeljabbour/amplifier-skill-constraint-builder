# Harness Machine Template Reference

This document explains how the harness machine templates work. The machine generator
(invoked via `/harness-execute` with `harness_scale=factory`) uses these templates
to stamp out a project-specific `.harness-machine/` directory.

## Template Variable Syntax

All templates use `{{variable_name}}` for placeholders. During generation, a **whitelist**
approach is applied: only known generation-time variables are replaced. All other `{{...}}`
patterns (Amplifier recipe runtime variables, Docker Go template strings) are preserved verbatim.

> **The generator MUST use a whitelist approach — only replace known generation-time variables.
> Any `{{}}` not in the whitelist must be preserved verbatim.**

This solves the dual-syntax problem: recipe files contain runtime `{{variables}}` like
`{{initial_state.status}}` and `{{iteration_result.status}}` that must survive into the
generated files unchanged. Only variables listed in the GENERATION-TIME whitelist below
get replaced.

---

## Variable Categories

### GENERATION-TIME Variables (replaced by generator, whitelisted)

These are replaced during the `.harness-machine/` stamping step. The generator substitutes
them with project-specific values.

| Variable | Description | Default |
|----------|-------------|---------|
| `project_name` | Short project identifier | *(required)* |
| `project_dir` | Absolute path to project root | *(required)* |
| `state_file` | Path to STATE.yaml | `{{project_dir}}/.harness-machine/STATE.yaml` |
| `context_file` | Path to CONTEXT-TRANSFER.md | `{{project_dir}}/.harness-machine/CONTEXT-TRANSFER.md` |
| `environment_specs_dir` | Path to environment specs directory | `{{project_dir}}/environments/` |
| `harness_spec` | Path to the harness specification document | *(required)* |
| `build_command` | Command to run harness evaluation | *(required)* |
| `test_command` | Command to run unit tests | *(required)* |
| `max_environments_per_session` | Environments to process per working session | `3` |
| `max_outer_iterations` | Max outer loop iterations before stopping | `50` |
| `session_timeout` | Working session timeout in seconds | `3600` |
| `cf_backoff` | Cloudflare challenge backoff in seconds | `900` |
| `cf_backoff_max` | Max CF preflight exponential backoff ceiling (seconds) | `2700` |
| `inter_session_cooldown` | Pause between successful sessions in seconds | `60` |
| `container_name` | Docker container name for the harness machine | `{{project_name}}-harness-machine` |
| `image_name` | Docker image name (tagged on build) | `{{project_name}}-harness-machine:latest` |
| `base_image` | Docker base image | `python:3.12-slim` |
| `uv_version` | Pinned uv version | `0.10.4` |
| `user_uid` | Host user UID (for Docker build arg USER_UID) | `1000` |
| `user_gid` | Host user GID (for Docker build arg USER_GID) | `1000` |
| `username` | Container username; must equal `basename $user_home` | *(required)* |
| `user_home` | Container user home directory (must match host `$HOME`) | `/home/$username` |
| `system_packages` | Additional apt packages, space-separated (may be empty) | *(empty)* |
| `node_setup` | Node.js installation commands (empty if not needed) | *(empty)* |
| `python_dev_tools` | Python dev tool installs via uv (ruff, pyright, etc.) | *(empty)* |
| `extra_pip_packages` | Additional system pip packages beyond pyyaml | *(empty)* |
| `install_deps_block` | Shell block for project dependency installation | *(empty)* |
| `bundle_dir` | Absolute path to the amplifier-bundle-autoharness checkout | *(required)* |
| `timestamp` | ISO 8601 timestamp of generation | *(auto-generated)* |

### RUNTIME Variables (must survive into generated files, NOT replaced)

These appear in recipe YAML files as Amplifier recipe context variables. The generator
must **not** replace them — they are resolved at recipe execution time by the Amplifier
runtime.

| Variable | Description | Appears In |
|----------|-------------|------------|
| `{{initial_state.status}}` | Status from read-state step | harness-machine-build.yaml |
| `{{initial_state.blockers}}` | Blockers list from read-state step | harness-machine-build.yaml |
| `{{iteration_result.iteration_result.status}}` | Status from iteration sub-recipe | harness-machine-build.yaml |
| `{{iteration_result.iteration_result.session_count}}` | Session count from iteration | harness-machine-build.yaml |
| `{{status}}` | Runtime loop status variable | harness-machine-build.yaml |
| `{{session_count}}` | Runtime session counter | harness-machine-build.yaml, iteration.yaml |
| `{{orient_state.next_env}}` | Next environment name from orient step | harness-machine-iteration.yaml |
| `{{orient_state.harness_type}}` | Harness type from orient step | harness-machine-iteration.yaml |
| `{{orient_state.harness_scale}}` | Harness scale from orient step | harness-machine-iteration.yaml |

### Docker Go Template Strings (must survive into generated files, NOT replaced)

These appear in monitoring scripts and are processed by Docker's Go template engine at
runtime. They look identical to Amplifier template variables but are completely separate.

| String | Description | Appears In |
|--------|-------------|------------|
| `{{.CPUPerc}}` | Docker container CPU percentage | watchdog.sh, monitor.sh |
| `{{.MemUsage}}` | Docker container memory usage | watchdog.sh, monitor.sh |
| `{{.State.Status}}` | Docker container state | monitor.sh |

---

## Template Files

### State Files (at project root, copied into `.harness-machine/`)

- `STATE.yaml` — machine-readable harness generation state (environments, status, epochs)
- `CONTEXT-TRANSFER.md` — session handoff document for constraint design decisions
- `SCRATCH.md` — ephemeral working memory (disposable between sessions)

### Recipes (in `.harness-machine/`)

- `build.yaml` — outer loop (from `templates/recipes/harness-machine-build.yaml`)
- `iteration.yaml` — inner loop: one environment per session (from `templates/recipes/harness-machine-iteration.yaml`)

### Infrastructure Scripts

- `scripts/entrypoint.sh` — container entrypoint with CF-aware retry loop
- `scripts/harness-machine-watchdog.sh` — host-side health watchdog (cron every 15 min)
- `scripts/harness-machine-monitor.sh` — diagnostic monitor with 5 failure-pattern detections (cron every 10 min)

### Infrastructure Config

- `harness-machine.Dockerfile` — container definition
- `docker-compose.harness-machine.yaml` — Docker Compose config

---

## How Generation Works

1. The `/harness-execute` mode (when `harness_scale=factory`) dispatches `harness-machine:harness-generator` agent
2. Agent reads the harness spec + plan to extract all variable values
3. For each template file:
   a. Reads the template from `templates/`
   b. Applies the whitelist: replaces ONLY variables listed in the GENERATION-TIME table
   c. Preserves all other `{{...}}` patterns verbatim (runtime vars, Docker Go templates)
   d. Writes the result to `.harness-machine/` in the project
4. Creates the `.harness-machine/` directory structure:
   ```
   .harness-machine/
     STATE.yaml
     CONTEXT-TRANSFER.md
     SCRATCH.md
     build.yaml
     iteration.yaml
     harnesses/      (empty, populated at runtime)
   ```
5. Copies Docker infrastructure to project root:
   - `harness-machine.Dockerfile`
   - `docker-compose.harness-machine.yaml`
   - `scripts/entrypoint.sh`
   - `scripts/harness-machine-watchdog.sh`
   - `scripts/harness-machine-monitor.sh`
6. Reports startup instructions (docker compose up -d, cron setup)

---

## Cron Setup (Host Side)

After generation, add these two cron jobs on the host machine:

```cron
# Harness machine watchdog — restart container if stuck (every 15 min)
*/15 * * * * {{project_dir}}/scripts/harness-machine-watchdog.sh

# Harness machine monitor — pattern detection + auto-remediation (every 10 min)
*/10 * * * * {{project_dir}}/scripts/harness-machine-monitor.sh
```

---

## Template Customization

Templates are designed to work as-is for most harness generation projects.
Customization happens through variables, not by modifying template structure.

The structural patterns (orient → generate → critique → refine → evaluate loops,
STATE.yaml persistence, session handoff via CONTEXT-TRANSFER.md) are proven patterns
from the AutoHarness paper and the dev-machine lineage. Do not change these patterns.

Domain-specific artifacts (harness spec, environment descriptions, evaluation code)
are created during the interactive pipeline phases (`/harness-explore`, `/harness-spec`,
`/harness-plan`), not from these templates.

Host monitor/watchdog scripts infer their project root from `<project>/scripts` at runtime, or accept `HARNESS_MACHINE_PROJECT_DIR` as environment data. They verify that root against Git and query container/image identity from Compose; do not render project paths into their shell/Python source. Docker Go-format tokens remain unchanged.
