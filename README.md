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

Requires Python 3.10+ (3.13 is what it is developed against) and Windows for
the integrated PowerShell terminal. The rest of the codebase is portable.

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
├── api.py            DeepSeek SSE client, error mapping, model discovery
├── tools.py          tool protocol, tag parser, sandboxed Workspace
├── web.py            search (ddgs, Bing RSS, DuckDuckGo HTML) and page extraction
├── checkpoints.py    pre-write snapshots and revert
├── memory.py         global and per-project note stores
├── usage.py          token accounting and USD pricing
│
├── chat.py           chat panel, composer, mode selectors, worker lifecycle
├── editor.py         code editor, gutter, highlighter, tab manager
├── terminal.py       persistent PowerShell session, git panel
├── panels.py         side panels: files, memory, brain, undo, settings
├── widgets.py        bubbles, tool cards, approval dialog, file tree
│
├── theme.py          palette, Qt palette override, global stylesheet
├── icons.py          painter-path icon set
├── render.py         markdown to Qt rich text, syntax colouring, diffs
├── config.py         settings dataclass, mode and model catalogues
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
results appended as a new turn ──► loop, until no tools are called
```

`AgentWorker` is a `QThread`. It never touches widgets; everything crosses the
boundary as a signal. Approval is the one place the worker blocks, waiting on a
`threading.Event` that the UI thread sets from the dialog result.

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
  key. Add the English side to `EN` in `i18n.py`.
- **Failures return, they do not raise.** Tools hand back `(False, message)`
  and the message goes to the model, which then has enough context to recover
  on its own.

## Threading

| Thread | Owns |
|---|---|
| Main | Every widget, the config object, all stores |
| `AgentWorker` | HTTP streaming, tool execution, checkpoint writes |
| `QProcess` | The PowerShell session, read asynchronously on the main thread |

The worker mutates stores (memory, checkpoints) directly. Those writes are
append-and-persist, and the UI reloads them on the `memory_changed` /
`tool_finished` signals rather than sharing live state.

## Theming

`theme.py` exports three things: the `C` colour dict, `palette()` and `qss()`.

The Qt palette override is not optional. Fusion paints scroll area viewports
and item views from the palette, not the stylesheet, so without it those
surfaces render white on a dark UI.

Widgets opt into styles by object name (`setObjectName("ToolCard")`) or by
dynamic property (`setProperty("kind", "primary")`). After changing a dynamic
property at runtime you must `unpolish`/`polish` the widget for the new rule to
apply.

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

There is no test suite yet. Before promoting to `main`, verify:

- [ ] Sandbox rejects `../x`, `C:\Windows\x` and `..\..\x`
- [ ] A write, an edit and a delete each appear in Undo and revert cleanly
- [ ] Approve mode shows a correct diff; Plan mode blocks mutating tools
- [ ] Auto mode completes a multi-step task without prompting
- [ ] Stop button cancels mid-stream and leaves no orphan thread
- [ ] Language switch restarts and the agent replies in the selected language
- [ ] Cost meter increments and matches the published rate
- [ ] Terminal keeps its working directory across commands
- [ ] `git status`, commit and push work from the source control panel
- [ ] Publishing to a fresh GitHub repository works from an empty folder
- [ ] Built executable launches with no Python on PATH

## Branches

| Branch | Purpose |
|---|---|
| `main` | Release-ready. Product README. |
| `develop` | Integration. This guide. |
| `docs` | Long-form documentation and reference. |

## License

MIT. See [LICENSE](LICENSE).
