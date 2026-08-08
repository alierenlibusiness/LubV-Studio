# Cost and models

[← Back to index](README.md)

## Models

The model list is fetched from your key at startup, so whatever you have access
to appears in Settings. Two are current:

| | V4 Flash | V4 Pro |
|---|---|---|
| Context | 1M tokens | 1M tokens |
| Input, cache hit | $0.0028 / 1M | $0.003625 / 1M |
| Input, cache miss | $0.14 / 1M | $0.435 / 1M |
| Output | $0.28 / 1M | $0.87 / 1M |
| Good for | Almost everything | Hard architecture, large refactors |

Flash is the default and is the right answer most of the time. Reach for Pro
when a task needs judgement rather than throughput: designing a module,
untangling a dependency knot, choosing between two approaches.

## Thinking mode

Both models reason before answering. Thinking mode is on by default and can be
turned off in Settings for faster, cheaper, shallower responses.

Reasoning tokens are billed as output tokens, and the cost meter counts them.

You can watch the reasoning stream in a collapsed box above each answer. Turning
that display off does not change the cost; it only hides it.

## What things cost

Cost is computed from the usage the API returns with every response, priced
against the table above, splitting cache-hit from cache-miss input.

Numbers from ordinary use:

| Turn | Tokens | Flash | Pro |
|---|---|---|---|
| Short question, no tools | ~1.3K | 0.02¢ | 0.06¢ |
| Read a file and explain it | ~6K | 0.09¢ | 0.28¢ |
| Read, edit, run, verify | ~54K | 0.40¢ | 1.23¢ |

The million token window means you can be generous with what you show the agent.
Attaching a few files to a message is cheap. Making it guess, and then paying
for three corrective round trips, is what actually costs money.

## Caching

DeepSeek caches prompt prefixes. Because the system prompt, memory and project
tree stay stable across a conversation, most input tokens hit the cache after
the first turn at roughly one fiftieth of the price. This is why a long
conversation costs far less than its raw token count suggests.

Two consequences worth knowing:

- Editing the brain mid-conversation invalidates the cached prefix.
- The first turn of a new chat costs slightly more than the ones after it.

Neither should change how you work; they just explain the numbers.

## Where the meter is

**Status bar:** session and today, always visible.

**Settings › Spending:** session, today, all time, and the last few days, with
token and request counts.

History is kept for 90 days in `~/.lubv_studio/usage.json`. The session counter
resets on restart, or with the reset button.

## Keeping the bill down

- Stay on Flash unless the task genuinely needs Pro.
- Prefer surgical edits. The agent already does; a brain rule reinforcing it
  helps on large files.
- Start a new chat when you switch tasks. Old context is dead weight you pay to
  carry.
- Use Plan mode before large work. One planning turn is cheaper than three wrong
  implementation turns.
- Lower `Max agent steps` if the agent over-verifies its own work.
