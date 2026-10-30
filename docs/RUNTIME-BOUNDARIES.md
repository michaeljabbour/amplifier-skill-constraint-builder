# Runtime and credential boundaries

The portable method and local checker do not install an operating-system sandbox.
Candidate checker Python is trusted code. The optional Pico, Nano and Micro
`LocalToolExecutor` checks explicit file-tool path arguments against `project_root`.
Its `bash` tool deliberately executes the caller's shell program with that root as
the working directory. A working directory is not a filesystem jail: shell programs
can use absolute paths, network connections, inherited credentials and subprocesses
with the current user's permissions. A prompt rule or constraint predicate is not
an independent OS boundary. Use a separately configured and tested OS/container
boundary when running untrusted programs; passing local gate tests does not prove
that every possible action is contained.

The optional Compose template limits host bind mounts and retains `cap_drop: ALL`,
`no-new-privileges:true`, a non-root container user and read-only bundle/config
mounts. It also uses host networking and gives the project and an Amplifier named
volume writable state. Every process in that container can read its environment
and provider key file, use those credentials, contact reachable services, and
modify its writable state. The project is the only writable host bind mount; it is
not the only place an agent can have effects. These templates have not been
accepted against a live Docker daemon as part of the local offline repair checks.

Set `HARNESS_MACHINE_KEYS_FILE` to an existing provider-only env file before
starting Compose. It must contain only the provider credentials this harness
needs. Do not supply Git credentials or unrelated account keys. The entrypoint
copies that same file into the container's Amplifier configuration. Read-only
mounts prevent edits to their host file; they do not hide readable credentials.
No SSH agent socket or `known_hosts` is mounted by default. A read-only socket
mount would still permit SSH signing, so it cannot separate an agent from another
process in the same container. Public source dependencies use HTTPS.

The monitor reports unpublished commits for owner review. It does not pull,
rebase, stash or push them automatically. Inspect changes and run any separately
authorized `git push` explicitly from the host. An `on_error: continue` policy in
an orchestration workflow does not confer publication authority or isolate a
credential.

The two upgrade recipes require the official Amplifier recipes engine's `step.env`
support. Recipe target paths and generated reports are environment data, never
inserted into Bash/Python source. Upgrade execution uses the exact backup receipt
from its backup step, validates source syntax before writing, and fails nonzero on
an invalid upgrade or validation. Python 3.11+ and PyYAML are required in the
Amplifier interpreter. `version_file` defaults to `context/version.md` relative to
the recipe working project; pass the installed bundle's version file when invoked
from another project. The minimal Micro recipe runner is not a replacement for
this staged engine and does not support this upgrade workflow's approval/state
contract. Upgrades preserve a sibling backup; they are not a promise of automatic
rollback after a partial filesystem failure.

The deterministic upgrade executor changes version metadata only. Its success result does not implement or verify an arbitrary generated migration plan. Source, tier and feature migrations require their own approved implementation and acceptance before a full-upgrade claim.

Host monitor/watchdog scripts infer the project root from their `<project>/scripts` location; `HARNESS_MACHINE_PROJECT_DIR` may override it as environment data. They require that directory to be the Git worktree root before any save or Docker operation, query container/image identity from Compose, pass paths as argv, and fail nonzero on critical errors. These are host automation programs: keep them and the Compose configuration trusted. Running agent-edited scripts/configuration from cron does not isolate the host from a hostile agent, even when container bind mounts are restricted. No live Docker acceptance is inferred from fake-command regressions.

### Native checker return contract

Both checker signatures must return a two-item tuple containing a literal `bool`
and a string reason. The hook does not coerce strings, numbers or objects to a
decision. Malformed results and checker exceptions deny the action even when
`strict: false`; that advisory setting only softens a valid `(False, reason)`
policy decision. This validates checker results; loading a checker still runs
trusted project Python and does not create an operating-system sandbox.
