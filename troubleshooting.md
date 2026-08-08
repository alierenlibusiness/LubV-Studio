# Troubleshooting

[← Back to index](README.md)

## Connection and keys

**Invalid API key (401)**
The key is wrong, truncated, or from a different provider. Re-copy it from
[platform.deepseek.com](https://platform.deepseek.com). Keys start with `sk-`.

**Insufficient balance (402)**
Your DeepSeek credit ran out. Top up; the key itself is fine.

**Too many requests (429)**
Rate limited. The agent now waits and retries this by itself, showing a note
while it does. If it still fails after several attempts, wait a minute.

**The balance in the top bar shows `--`**
It could not be read. Hover it for the reason: usually no key entered yet, or
no network. Click it to retry. It refreshes on a timer and again whenever a
request finishes, so it should not stay stale for long.

**Test connection hangs**
Usually a corporate proxy or a VPN interfering with TLS. Try without the VPN
first to isolate it.

## The agent

**It says it will do something and then does not**
The tags never got emitted. The loop notices this and prompts the agent to
carry on, so it usually recovers by itself. If it happens every time, the brain
is arguing against tool use, for example a rule like "always show me the code
instead of changing files". Check the Brain panel for an instruction that
contradicts what you are asking.

**It stops in the middle of a long job**
This should no longer happen on its own. There is no step limit unless you set
one, an interrupted stream resumes, and a transient API error is retried. If it
still stops, look at the last card in the chat:

- A red card with the same error several times over means the loop hit the
  no-progress guard: it was repeating one failing action with no effect. Read
  the error and give it a different angle.
- *"The task did not finish in N steps"* means you have a step limit set. Put
  `Max agent steps` back to 0 in Settings for no limit.
- A message about the balance means the account ran out of credit. The top bar
  shows what is left.

**Edits keep failing with "the old block was not found"**
The agent is working from a stale copy. Tell it to re-read the file. If it keeps
happening on one file, that file probably has mixed line endings or tabs;
normalising it fixes the matching. Repeated identically, this is what trips the
no-progress guard.

**I typed something while it was working and nothing happened**
It was not lost. A message sent mid-task is handed to the running job and shows
*"Added to the running job"*; one sent in the instant a job ends is queued and
shows in the strip above the input. Stop clears anything still queued.

**It keeps running longer than I expected**
There is no step limit by default, which is what makes it finish long jobs
unattended. Watch the balance in the top bar, press Stop whenever you want, or
set `Max agent steps` in Settings for a hard ceiling.

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
config.json      settings, prompt rules and API key
memory/          your notes
sessions/        saved chats
checkpoints/     previous versions of edited files
usage.json       spend history
```

Delete the folder for a full reset. Delete `config.json` alone to keep memory
and history but re-enter the key. Delete `sessions/` to clear saved chats, which
the *Delete all* button in the Sessions panel also does.

**A saved chat will not open**
Its file is corrupt and gets skipped. Delete that one session from the panel.
`sessions/index.json` is only a cache of the list; deleting it is safe, it is
rebuilt from the session files on the next refresh.
