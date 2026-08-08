# Troubleshooting

[← Back to index](README.md)

## Connection and keys

**Invalid API key (401)**
The key is wrong, truncated, or from a different provider. Re-copy it from
[platform.deepseek.com](https://platform.deepseek.com). Keys start with `sk-`.

**Insufficient balance (402)**
Your DeepSeek credit ran out. Top up; the key itself is fine.

**Too many requests (429)**
Rate limited. Wait a few seconds and resend. Nothing is lost.

**Test connection hangs**
Usually a corporate proxy or a VPN interfering with TLS. Try without the VPN
first to isolate it.

## The agent

**It says it will do something and then does not**
The tags never got emitted. Almost always a brain that argues against tool use,
for example a rule like "always show me the code instead of changing files".
Check the Brain panel for an instruction that contradicts what you are asking.

**Edits keep failing with "the old block was not found"**
The agent is working from a stale copy. Tell it to re-read the file. If it keeps
happening on one file, that file probably has mixed line endings or tabs;
normalising it fixes the matching.

**"The task did not finish in N steps"**
It ran out of its step budget, usually stuck in a verify-and-fix loop. Raise
`Max agent steps` in Settings, or split the task.

**Answers come back in the wrong language**
Response language follows the interface language. Change it in Settings; the app
restarts and the next answer follows.

## Files and terminal

**A file I expected is missing from the tree**
The tree hides `.git`, `__pycache__`, `node_modules`, `.venv`, `.idea` and
similar. Everything else is shown, including `dist` and `build`.

**The agent cannot see a file outside the project**
By design. The workspace root is the boundary. Open that folder as the project
instead, or copy the file in.

**Terminal shows nothing**
Some commands buffer their output until they exit, so a long-running process
looks frozen and then flushes all at once. Press **Restart** to kill the shell
and start a clean session.

**A command is waiting for input**
Interactive prompts are not supported in the embedded shell. Add the
non-interactive flag (`-y`, `--yes`, `--no-input`) or run it in a real terminal.

## Git

**Git not found**
Install it from [git-scm.com](https://git-scm.com) and restart the app so the
new PATH is picked up.

**Push asks for credentials and nothing happens**
Git Credential Manager opens its own window, which can appear behind the app.
Alt-Tab to it. Once you authenticate the first time it is remembered.

**Says everything is clean but I changed files**
The editor still holds unsaved buffers. `Ctrl+Shift+S` saves all, then refresh
the source control panel.

## The executable

**Windows SmartScreen warns about it**
Expected for an unsigned binary. *More info → Run anyway*. Signing needs a code
signing certificate, which this project does not have.

**Antivirus quarantines it**
PyInstaller one-file binaries are a common false positive because they unpack
themselves into a temp directory at launch. Add an exclusion, or run from source.

**It takes a few seconds to start**
Also the unpacking. Only the first launch after a reboot is slow.

## Resetting

Everything the app remembers lives in `~/.lubv_studio/`:

```
config.json      settings and API key
memory/          your notes
checkpoints/     previous versions of edited files
usage.json       spend history
```

Delete the folder for a full reset. Delete `config.json` alone to keep memory
and history but re-enter the key.
