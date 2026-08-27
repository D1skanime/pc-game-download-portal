# Repository Instructions

Read and follow [CLAUDE.md](CLAUDE.md) for all repository instructions.

## Remote GSD Coordination

For GSD work, the chat is the control plane and `/home/d1sk/romm` is the execution plane.

- The user communicates only through the chat. Do not ask the user to type GSD commands, start agents, tail logs, or relay terminal output unless they explicitly request diagnostic access.
- Before a write action, verify the Linux host, canonical checkout, branch, and planning state as described above.
- Run implementation, planning artifacts, tests, commits, and deployment only on the Linux checkout through a Codex agent.
- Keep interactive GSD discussion in chat. A remote Codex agent may gather context or execute an approved plan, but its questions must be returned to the user in chat, in German, with concise numbered choices.
- Batch independent discussion decisions into one message. Do not make the user repeat an invocation or issue a new command after each answer. Resume the remote agent with the captured answers.
- The coordinating agent owns progress monitoring and must report meaningful changes without requiring the user to watch logs. Do not claim a background agent is interactive with chat when no input bridge exists.
- Preserve unrelated worktree changes and do not deploy, access a real NAS mount, restart Team4s, or alter Team4s unless the active task explicitly authorizes it.
