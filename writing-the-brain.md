# Writing the brain

[← Back to index](README.md)

The Brain panel holds the system prompt. Whatever is in that box is sent, in
full, at the top of every request. The application adds exactly one thing after
it: the tool protocol, which is the list of tags the agent uses to read files,
run commands and so on. Without that block the agent has no hands.

Nothing else is inserted. There is no hidden preamble, no personality shim, no
extra layer of instructions between what you wrote and what the model receives.

## What actually gets sent

In order:

1. **Your brain:** verbatim.
2. **Response language:** one short block telling the model to answer in the
   interface language you selected.
3. **Mode instructions:** only in Plan or Auto mode, describing that mode's
   constraints.
4. **Persistence rule:** the instruction not to abandon a job half done and to
   signal completion explicitly. Skipped in Plan mode, where nothing is applied.
5. **Prompt rules:** your rules for how requests should be written, so the agent
   can tell you what a vague request was missing. Editable in Settings, and
   switchable off there.
6. **Memory:** your saved notes, if memory is enabled.
7. **Project context:** root path, OS, shell, open editor tabs, and the file tree.
8. **Tool protocol:** the tags and the rules for using them.

Items 2 through 8 are generated. Items 1 and 5 are yours.

Two of the generated blocks exist to keep the agent working rather than to
shape its character, and it is worth not fighting them from the brain. A rule
like *"always stop and ask me before doing anything"* contradicts the
persistence rule and produces an agent that stalls and then gets prompted to
continue. If you want that behaviour, use **Approve** mode, which gates every
action properly, instead of arguing for it in prose.

## What makes a brain work well

**Be concrete about behaviour, not tone.** "Read the file before editing it" and
"never leave a function without error handling" change output. "Be helpful"
does not.

**Say what to do when it is unsure.** Ask? Assume and note the assumption? Pick
the most common convention? Without a rule, the model will pick one at random
each time.

**Set the verbosity.** Models default to explaining. If you want code and one
line of summary, say so, and it will hold.

**Name your stack.** Framework, version, formatter, naming style, test runner.
This saves an entire round trip of wrong guesses on every task.

**Keep it under a page.** A long prompt does not make the model more obedient,
it dilutes the parts you care about. Anything project-specific belongs in
[Memory](README.md#the-short-version-of-everything), which is injected the
same way but stays editable per project.

## A starting point

```
You are my coding agent on this project.

Working style:
- Read before you write. Never guess file contents.
- Small changes: edit the exact block. Large ones: say why before rewriting.
- After finishing, one short paragraph: what changed and what to check.
- If a requirement is ambiguous and the choice matters, ask. Otherwise decide
  and say what you decided.

Stack: Python 3.13, PySide6, no external formatter, 4-space indent.
Prefer standard library. Do not add a dependency without saying why first.

Do not apologise. Do not restate my request back to me. Do not add comments
that describe what the next line does.
```

## Memory versus brain

| | Brain | Memory |
|---|---|---|
| Scope | Global, one prompt | Per project or global notes |
| Edited by | You | You and the agent |
| Good for | Behaviour, style, hard rules | Facts, decisions, preferences |

"Always write tests" is a brain rule. "The auth module uses the old callback
style, do not modernise it" is a memory note.

The agent can add its own memory notes when it learns something durable. You can
see, edit and delete all of them in the Memory panel.

## Scope

The brain controls how the agent behaves inside this application. It does not
change the model provider's own policies, which apply to the API response no
matter what any client sends. What LUBV Studio guarantees is that it adds no
layer of its own on top of yours.
