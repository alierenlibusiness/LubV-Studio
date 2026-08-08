# LUBV Studio, Developer Guide

> This is the `develop` branch: the integration branch where work lands before
> it is promoted to `main`. Same code, developer-facing documentation.
> For the product overview, see [`main`](../../tree/main).

---

## Getting set up

```bash
git clone -b develop https://github.com/alierenlibusiness/LubV-Studio.git
cd LubV-Studio
python -m venv .venv && .venv\Scripts\activate
pip install -r requirements.txt
python -m lubv_studio
```

Requires Python 3.10+ (3.13 is what it is developed against). Runs on Windows
and macOS; Linux works but gets less testing.

Run against an arbitrary folder without touching your saved config:

```bash
python -m lubv_studio C:\some\other\project
```

## Module map

```
lubv_studio/
├── app.py            entry point: palette, font, icon, language, restart loop
├── main_window.py    three-column shell, rail, panel stack, status bar, shortcuts
│
├── agent.py          the loop: prompt assembly, streaming, tool dispatch, approval
├── api.py            DeepSeek SSE client, error mapping, model discovery, balance
├── balance.py        background thread polling the remaining API credit
├── tools.py          tool protocol, tag parser, sandboxed Workspace
├── web.py            search (ddgs, Bing RSS, DuckDuckGo HTML) and page extraction
├── checkpoints.py    pre-write snapshots and revert
├── memory.py         global and per-project note stores
├── sessions.py       saved chats: transcript, model history, index, pruning
├── usage.py          token accounting and USD pricing
│
├── chat.py           chat panel, composer, mode selectors, worker lifecycle, queue
├── editor.py         code editor, gutter, highlighter, tab manager
├── terminal.py       persistent shell session with completion tracking, git panel
├── panels.py         side panels: files, sessions, memory, brain, undo, settings
├── widgets.py        bubbles, tool cards, approval dialog, file tree, balance badge
│
├── theme.py          palette, Qt palette override, global stylesheet
├── icons.py          painter-path icon set
├── render.py         markdown to Qt rich text, syntax colouring, diffs
├── config.py         settings dataclass, mode and model catalogues
├── platform_.py      every OS difference: shell, fonts, icon format
└── i18n.py           translation table
```

## How a turn works

```
user message
   │
   ▼
build_system_prompt()      brain + response language + mode + memory
   │                       + project tree + tool protocol
   ▼
DeepSeekClient.stream()    yields content / reasoning / usage deltas
   │
   ├─► StreamTagFilter     hides tool tags from the visible stream
   │
   ▼
parse_tool_calls()         extracts calls in order of appearance
   │
   ├─► approval gate       blocks the worker thread until the UI answers
   │
   ▼
tools.execute()            runs inside the sandbox, checkpointing first
   │
   ▼
results appended as a new turn ──► loop, until <TASK_DONE>
```

`AgentWorker` is a `QThread`. It never touches widgets; everything crosses the
boundary as a signal. Approval is the one place the worker blocks, waiting on a
`threading.Event` that the UI thread sets from the dialog result.

### Why the loop does not end on "no tool calls"

It used to, and that was the single biggest source of "the agent stopped by
itself". A reply like *"now I will open that file"* contains no tag, so the
turn ended with the work undone. Completion is now explicit: the model has to
emit `<TASK_DONE>`. Four things fall out of that decision.

- **`TASK_DONE` is parsed but is not a tool.** `parse_tool_calls` skips it and
  `gorev_bitti_mi()` answers the loop's question separately.
- **It is not in `OPEN_TAGS`.** The prompts allow a bodyless `<TASK_DONE>`, so
  feeding it to `StreamTagFilter`'s open/close machinery would swallow every
  remaining character when the closing tag never arrived. It is stripped as a
  standalone token instead, in all four spellings.
- **Nudges are bounded** by `MAX_DURTU`. A model that answers without tags and
  without finishing is prompted to continue, then the loop gives up rather than
  trading empty turns forever.
- **Turns are unbounded by default** (`max_iterations = 0`), so the only
  structural protection left is `MAX_KISIR_TUR`: if the identical set of tool
  calls fails identically several turns running, the loop stops. Progress of
  any kind resets the counter, so a long legitimate task is never cut short.

### Failure handling in the stream

`_bir_tur()` distinguishes two cases, and the distinction matters because
retrying is not always safe:

- **Nothing streamed yet** and `_gecici_hata()` says the error is transient
  (429, 5xx, dropped connection): retry with backoff. Permanent errors (401,
  402, 403) raise immediately, since waiting cannot fix a bad key.
- **Partial answer already streamed**: never retry, that would duplicate the
  visible text. Return what arrived and let the loop send a continuation turn.

"Is this worth retrying" is answered by `ApiError.gecici`, set from the HTTP
status against `GECICI_KODLAR`. It used to be answered by matching words in the
message, which broke the moment those messages were translated. The flag
defaults to `None`, not `False`: an unmarked error falls back to the text
heuristics, so forgetting to mark a new transient error degrades to the old
behaviour instead of silently disabling retries for it.

### Messages that arrive mid-run

`mesaj_ekle()` takes a message under a lock and returns `False` once the loop
has closed. The UI uses that answer to decide: `True` means the running job
absorbed it, `False` means queue it and start a fresh run in `_bitti`. The
`_basliyor` flag covers the gap between scheduling that run and it actually
starting, so a fast typist cannot start a second `AgentWorker` over the first.

## Adding a tool

Four edits, no framework:

1. **`tools.py`**: add the tag name to `TAG_NAMES`, map it in `_KIND_BY_TAG`,
   give it a label in `TOOL_LABELS` and an icon key in `TOOL_ICONS`.
2. **`tools.py`**: document the tag in `TOOL_PROTOCOL` with a concrete example.
   The model only knows what this string tells it.
3. **`tools.py`**: implement it on `Workspace` and dispatch it in `execute()`.
   Return `(ok: bool, output: str)`.
4. **`icons.py`**: draw the icon if you used a new key.

If the tool mutates state, add it to `needs_approval_kind` so it goes through
the approval gate, and call `_checkpoint()` before writing so it can be undone.

Give it a line in `sonuc_ozeti()` too. The card badge used to show elapsed time,
which read `0.0s` for anything fast and made a successful read look like nothing
had happened; it now reports the actual result, so a new tool without a summary
line falls back to a duration and looks broken next to the others.

## Git integration

`GitPanel` never shells out silently: every action is emitted as a command
string and executed in the visible terminal, so the user reads git's own
output rather than a summarised version of it.

Three things it guarantees before any commit or push:

- a repository exists (`git init` if not),
- at least one commit exists, checked by exit code because `git rev-parse HEAD`
  prints `HEAD` to stdout on an empty repository and looking at stdout gives
  the wrong answer,
- a git identity is configured, asked once and prefilled from the GitHub CLI
  account when one is signed in.

`github_adresi()` normalises `user/repo`, bare hostnames, full https URLs and
ssh URLs into one canonical form; it returns an empty string for anything it
does not recognise, which the caller treats as invalid input.

## Platform differences

`platform_.py` is the only module that reads `sys.platform`. Everything that
differs by OS asks it:

| Concern | Windows | macOS |
|---|---|---|
| Terminal shell | `pwsh` if present, else `powershell.exe`, `-Command -` | `$SHELL` or `/bin/zsh` |
| UI font | Segoe UI | SF Pro Text |
| Monospace font | Cascadia Mono | SF Mono |
| Window icon | `.ico` | `.icns` |
| Packaging | one-file `.exe` | `.app` bundle |

Two rules follow from this. Never write shell-specific syntax into a command
string: resolve the condition in Python and emit plain commands. Never hardcode
a font family: ask for the candidate list and take the first one the system
actually has.

Agent commands go through `komut_argumanlari()` rather than `shell=True`, so
they run in the same shell the terminal panel shows. One exception is encoded
there: Windows PowerShell 5.1 cannot parse `&&` or `||`, and models emit
`cd app && npm install` constantly, so those commands are handed to `cmd.exe`.
PowerShell 7 parses them natively and keeps the normal path.

`creationflags=GIZLI_PENCERE` is set on every `subprocess` call. Without it the
packaged executable flashes a console window on each git query.

### Terminal completion protocol

A shell fed from stdin gives no prompt, so "did the command finish, what was
the exit code, where are we now" is unanswerable by reading output alone. After
each user command the panel writes a second, hidden line built by
`bitis_isareti_komutu()`, which prints a per-session random marker followed by
the exit code and `$PWD`. `_satir_isle()` recognises the marker, removes it from
the visible output and updates the status strip and working directory.

The marker can be split across two `readyRead` chunks, which is why the partial
buffer is only flushed when `_isaret_baslangici_olabilir()` says the tail cannot
be the beginning of a marker. Printing half a marker and clearing the buffer
would leave the other half unmatchable and hang the "running" state forever.

## Conventions

- **Language.** Identifiers, comments and docstrings are Turkish; the public
  README and commit messages are English. Keep new code consistent with the
  file it lives in.
- **Comments explain why.** Not what the next line does. Most of the comments
  in this codebase exist because a naive implementation was wrong first.
- **No magic numbers in styles.** Radii and spacing come from `theme.py`.
  Colours come from the `C` dict, never inline hex, so a palette change is one
  edit.
- **User-visible strings go through `t()`.** The Turkish source string is the
  key. Add the English side to `EN` in `i18n.py`. This includes strings raised
  from worker threads and from `api.py`: they land in chat bubbles like any
  other text. If any logic then branches on those strings, that logic is now
  broken, so give the object a field to branch on instead.
- **Failures return, they do not raise.** Tools hand back `(False, message)`
  and the message goes to the model, which then has enough context to recover
  on its own.

## Threading

| Thread | Owns |
|---|---|
| Main | Every widget, the config object, all stores |
| `AgentWorker` | HTTP streaming, tool execution, checkpoint writes |
| `BalanceWatcher` | Polling `/user/balance`, nothing else |
| `QProcess` | The shell session, read asynchronously on the main thread |

The worker mutates stores (memory, checkpoints) directly. Those writes are
append-and-persist, and the UI reloads them on the `memory_changed` /
`tool_finished` signals rather than sharing live state.

`BalanceWatcher` is deliberately **not** parented to `MainWindow`. A Qt parent
would destroy it during teardown while it might still be blocked in `requests`,
which aborts the process. Python holds the only reference, `durdur()` sets its
stop event, and its request timeout is kept short so `wait()` on close returns
quickly. `hemen_yenile()` wakes it early, which is how the balance refreshes the
instant a request finishes instead of on the next tick.

## Sessions

A session stores two parallel records and the split is the whole design:

- `mesajlar` is what the model sees. It gets trimmed by `history_limit`.
- `olaylar` is what the user saw: bubbles, tool cards with their output, system
  notes. Never trimmed, and it is what `_dokumu_ciz()` replays on reopen.

Trimming the model history must not erase the user's transcript, and replaying
the transcript must not resend tool output to the model, so they cannot be the
same list. `_gecmisi_kirp()` additionally pins the first user message: dropping
the original request was how a long task lost track of what it was doing.

`SessionStore` keeps an `index.json` of lightweight summaries. The panel
refreshes on every completed request, and reading every session file each time
became visible once sessions accumulated. A missing or corrupt index is rebuilt
from the session files on the next read, so it is a cache and never the source
of truth.

## Theming

`theme.py` exports three things: the `C` colour dict, `palette()` and `qss()`.

The Qt palette override is not optional. Fusion paints scroll area viewports
and item views from the palette, not the stylesheet, so without it those
surfaces render white on a dark UI.

Widgets opt into styles by object name (`setObjectName("ToolCard")`) or by
dynamic property (`setProperty("kind", "primary")`). After changing a dynamic
property at runtime you must `unpolish`/`polish` the widget for the new rule to
apply.

## Layout traps

A `QSplitter` pane can never be dragged smaller than the sum of its children's
minimum widths, and a plain `QLabel` reports its full text width as that
minimum. One long label is therefore enough to freeze an entire column.

That is exactly what happened: the terminal header held the full project path,
and two welcome-screen labels did not wrap. Between them the centre column
claimed a 591px minimum, which on a 1234px window left the file panel pinned at
its own 240px minimum with no slack, so dragging its handle did nothing at all.

The rule for anything placed in a splitter pane: text that can be arbitrarily
long must either wrap (`setWordWrap(True)`) or elide. Eliding needs three
things together, and the path label does all three:

```python
etiket.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
etiket.setMinimumWidth(0)
# ve resizeEvent icinde QFontMetrics.elidedText ile yeniden yaz
```

`QSizePolicy.Ignored` alone is not enough, because `minimumSizeHint` still
comes from the text. `ToolCard.hedef` uses the same pattern for the same
reason.

Verify a change here by dragging, not by `setSizes()`: `setSizes` silently
normalises against the same constraints and will happily report a layout the
user cannot actually reach. `moveSplitter()` is what a drag does.

## Persisted UI state

`window_geometry` and `splitter_state` live in `config.json` as base64 of Qt's
own `saveGeometry()` / `saveState()` blobs, the two splitter states joined by
`|`. They are written in `closeEvent` and applied at the top of
`_pencereyi_yerlestir()`, which returns early when a restore succeeds so the
proportional first-run layout only runs on a fresh install.

A restored geometry is discarded when it no longer intersects the available
screen area. Without that check, unplugging a second monitor leaves the app
opening off-screen with no way to drag it back.

## Building

```bash
python build_exe.py
```

Cleans previous output, installs PyInstaller if missing, and produces a one-file
windowed executable in `dist/`. Unused Qt modules (WebEngine, Quick, Charts,
3D, Multimedia) are excluded; without those exclusions the binary roughly
doubles. `--collect-all ddgs` is required or the search backend loses its data
files at runtime.

## Manual test pass

There is no automated suite in the repository yet. Before promoting to `main`,
verify:

**Agent loop**

- [ ] A task needing more than a dozen steps runs to completion without a limit error
- [ ] A reply with no tool call and no `<TASK_DONE>` gets nudged, not ended
- [ ] `<TASK_DONE>` written bodyless at the end of a sentence still shows the sentence
- [ ] A repeated identical failure stops with the no-progress message
- [ ] Stop button cancels mid-stream and leaves no orphan thread
- [ ] A message typed mid-task lands in the same job; one typed as it ends gets queued

**Sessions**

- [ ] A chat survives a restart and reopens with its tool cards intact
- [ ] Rename, delete and clear all behave, and the index stays consistent
- [ ] Deleting `index.json` by hand rebuilds it with no data loss

**Workspace**

- [ ] Sandbox rejects `../x`, `C:\Windows\x` and `..\..\x`
- [ ] A write, an edit and a delete each appear in Undo and revert cleanly
- [ ] Approve mode shows a correct diff; Plan mode blocks mutating tools
- [ ] Tabs close from their own button after being reordered
- [ ] A modified tab shows a dot that does not move the close button
- [ ] Folder arrows point right when collapsed and down when open
- [ ] Highlighting distinguishes builtins, literals and declarations
- [ ] The file panel can be **dragged** wider and narrower, with a long project
      path open and the welcome screen showing
- [ ] Window size and both splitter positions survive a restart
- [ ] A geometry saved on a monitor that is now unplugged falls back to the
      default layout instead of opening off-screen

**Shell and cost**

- [ ] Terminal keeps its working directory across commands, including after `cd`
- [ ] A finished command reports its exit code and duration
- [ ] `cd app && echo x` works from the agent on PowerShell 5.1 and on pwsh
- [ ] Balance appears in the top bar and drops after a request
- [ ] Cost meter increments and matches the published rate
- [ ] `git status`, commit and push work from the source control panel
- [ ] Publishing to a fresh GitHub repository works from an empty folder

**Packaging and i18n**

- [ ] Built executable launches with no Python on PATH, with no console flash
- [ ] Language switch restarts and the agent replies in the selected language
- [ ] Every new string added this cycle has an `EN` entry

## Branches

| Branch | Purpose |
|---|---|
| `main` | Release-ready. Product README. |
| `develop` | Integration. This guide. |
| `docs` | Long-form documentation and reference. |

## License

MIT. See [LICENSE](LICENSE).
