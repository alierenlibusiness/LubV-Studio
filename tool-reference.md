# Tool reference

[← Back to index](README.md)

The agent acts by emitting tags inside its reply. The application parses them in
order of appearance, executes them, and feeds the results back as a new turn.
Tags never appear in the chat; they are filtered out of the stream as it arrives
and replaced with a card showing what happened.

You do not need to know any of this to use the app. It is here because the
protocol is the contract, and because this syntax is what you would extend if
you added a tool.

## File tools

### Read

```
<FILE_READ>
path/to/file.py
</FILE_READ>
```

Returns the file with line numbers. Files over 500 KB are refused. If the path
does not exist, the error lists similarly named files, which usually lets the
agent correct itself without another round trip.

### Edit

```
<FILE_EDIT>
path/to/file.py
---ESKI---
the exact text to replace
---YENI---
what replaces it
</FILE_EDIT>
```

The preferred way to change an existing file. The old block must match byte for
byte and must be unique; if it appears more than once the edit is rejected with
a note to include more surrounding context. Cheaper and far safer than resending
a whole file.

### Write

```
<FILE_WRITE>
path/to/file.py
---
the complete contents of the file
</FILE_WRITE>
```

Creates a new file or replaces an existing one entirely. Parent directories are
created as needed. If the model wraps the body in a fenced code block, the fence
is stripped.

### Delete

```
<FILE_DELETE>
path/to/file.py
</FILE_DELETE>
```

Requires approval unless you have disabled the prompt for deletions.

### List

```
<FILE_LIST>
subfolder
</FILE_LIST>
```

Directories first, then files with sizes. Noise directories such as `.git`,
`__pycache__`, `node_modules` and `.venv` are skipped.

### Search

```
<FILE_SEARCH>
text to find
</FILE_SEARCH>
```

Case-insensitive full text search across the workspace, limited to text file
extensions. Returns `path:line: matching text`, capped at 80 hits.

## Shell

```
<RUN_COMMAND>
python -m pytest -q
</RUN_COMMAND>
```

Runs in the project directory through PowerShell. Output is merged (stdout and
stderr), truncated at 20,000 characters, and prefixed with the exit code so the
agent can tell success from failure. Default timeout is 120 seconds, adjustable
in Settings.

## Web

### Search

```
<WEB_SEARCH>
pyside6 qsplitter setSizes example
</WEB_SEARCH>
```

Returns titles, URLs and snippets. Three backends are tried in order, so a
single provider blocking requests does not take the feature down.

### Fetch

```
<WEB_FETCH>
https://doc.qt.io/qtforpython-6/PySide6/QtWidgets/QSplitter.html
</WEB_FETCH>
```

Downloads a page and reduces it to readable text: scripts, styles and markup
removed, whitespace collapsed, truncated at 18,000 characters. JSON endpoints
are returned unchanged.

## Memory

```
<MEMORY_ADD>
This project targets Python 3.10, do not use match statements.
</MEMORY_ADD>
```

Writes a durable note that is injected into every future request. Visible and
editable in the Memory panel.

## The sandbox

Every file path is resolved to an absolute path and then checked to be inside
the project root. Rejected before any I/O happens:

```
../secrets.txt              outside the root
..\..\Windows\system.ini    outside the root
C:\Users\me\.ssh\id_rsa     absolute, outside the root
```

Absolute paths that do land inside the project root are allowed.

This applies to file operations. Shell commands are not sandboxed; they run with
your user account's permissions, exactly as if you had typed them into a
terminal yourself. That is the point of having a shell, but it is worth knowing
before leaving Auto mode running on something you have not read.

## Approval

| Tool | Asks first |
|---|---|
| Write, Edit | Yes, with a diff |
| Delete | Yes, with the file contents |
| Run command | Yes, with the command |
| Read, List, Search, Web, Memory | No |

Approval can be disabled per action type in Settings, or globally by switching
to Auto mode. Plan mode blocks the mutating tools entirely, at the dispatcher,
regardless of settings.
