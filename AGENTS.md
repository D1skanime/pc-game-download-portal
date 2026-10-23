# Repository Instructions

Read and follow [CLAUDE.md](CLAUDE.md) for all repository instructions.

## Remote GSD Coordination

For GSD work, the chat is the control plane and `/home/d1sk/pc-game-download-portal` is the execution plane.

- The user communicates only through the chat. Do not ask the user to type GSD commands, start agents, tail logs, or relay terminal output unless they explicitly request diagnostic access.
- Before a write action, verify the Linux host, canonical checkout, branch, and planning state as described above.
- Run implementation, planning artifacts, tests, commits, and deployment only on the Linux checkout through a Codex agent.
- Keep interactive GSD discussion in chat. A remote Codex agent may gather context or execute an approved plan, but its questions must be returned to the user in chat, in German, with concise numbered choices.
- Batch independent discussion decisions into one message. Do not make the user repeat an invocation or issue a new command after each answer. Resume the remote agent with the captured answers.
- The coordinating agent owns progress monitoring and must report meaningful changes without requiring the user to watch logs. Do not claim a background agent is interactive with chat when no input bridge exists.
- Preserve unrelated worktree changes and do not deploy, access a real NAS mount, restart Team4s, or alter Team4s unless the active task explicitly authorizes it.

- Apply the repository-wide code-size and decomposition rules in CLAUDE.md to every implementation, regardless of which agent, model, phase, or AI tool performs the work.

## Documentation completion rule

Follow the "Documentation stays current with implementation" policy in `CLAUDE.md` for every feature and refactor. Include affected domain comments, architecture and workflow descriptions in the same task and PR. Plans, review and verification must account for this work; phase identifiers alone are not domain documentation.

## Git workflow

- The canonical development checkout is `/home/d1sk/pc-game-download-portal` on `team4s-linux`.
- The remote is `https://github.com/D1skanime/pc-game-download-portal.git`.
- Start implementation work from a fresh or up-to-date local feature branch based on `main`. Do not use the old `/home/d1sk/romm` checkout as a development base.
- After implementation and verification, commit the project changes in the Linux checkout with a concise English commit message. Never commit secrets, filled environment files, ROMs, media, databases, or local runtime state.
- Push the feature branch to the new repository and open a pull request against `main`. Do not push feature work directly to `main` unless the user explicitly requests direct main updates.
- Before any commit or push, run the relevant tests and repository verification checks, inspect `git status`, and confirm the intended diff.
