# Babel Persistent Codex Session

Date: 2026-07-09

Goal: keep a persistent Codex CLI session on Babel so the project can be controlled from a phone through SSH plus `tmux`.

## Current Session

- Host alias: `babel`
- Current Babel login node: `login4`
- Project root on Babel: `$HOME/4blue2brown_explore/repo`
- Codex CLI: `$HOME/.local/bin/codex`
- Codex version observed: `codex-cli 0.142.5`
- Persistent session name: `4b2b-codex`

The `4b2b-codex` tmux session has been moved to `login4`. The earlier `login3` session was checked and is no longer present. At creation time the `login4` session reached the Codex CLI main UI after skipping the CLI update prompt.

Observed warning: `codex_apps` MCP failed with an expired authentication token. This does not block normal Codex CLI usage, but app/connectors may require re-authentication before they work inside that remote session.

## Phone Workflow

From a phone SSH client such as Blink Shell or Termius:

```bash
ssh babel
tmux attach -t 4b2b-codex
```

If `ssh babel` lands on a different login node, connect to `login4` first or re-run `ssh babel` until `hostname` reports `login4`. The session is node-local because `tmux` runs on the login node where it was created.

If Codex is still on the trust prompt, choose `1. Yes, continue` for this project directory.

Detach without stopping the session:

```text
Ctrl-b d
```

List sessions:

```bash
tmux ls
```

Reattach later:

```bash
tmux attach -t 4b2b-codex
```

## Recreate If Needed

If the session is gone:

```bash
tmux new-session -s 4b2b-codex -c $HOME/4blue2brown_explore/repo $HOME/.local/bin/codex
```

For a detached startup:

```bash
tmux new-session -d -s 4b2b-codex -c $HOME/4blue2brown_explore/repo $HOME/.local/bin/codex
```

## GPU / Long Jobs

Use the login node for orchestration, editing, lightweight repo commands, and submitting jobs. Do not run long rendering, model inference, or training directly on the login node.

For GPU work, request a Slurm job from inside the Codex/tmux session, for example:

```bash
srun -p debug --gres=gpu:1 --time=00:10:00 --mem=16G --cpus-per-task=4 --pty bash
```

Once inside the allocated GPU node, run the render or inference command there.

## Practical Notes

- This setup is persistent because `tmux` survives SSH disconnects.
- It is not a public web control panel; SSH remains the access boundary.
- If phone control becomes too awkward, the next layer would be a small queue-based runner: phone posts a task, Babel Codex/agent consumes it, writes logs/artifacts, and optionally sends status back to Slack or a web page.
