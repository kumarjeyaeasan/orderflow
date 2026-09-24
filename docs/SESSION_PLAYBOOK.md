# Session Playbook — working with Claude Code in VS Code

## Starting a session
Paste one of these into the Claude Code panel.

**Start or resume a phase**
```
Read docs/PROGRESS.md and the current phase in docs/ROADMAP.md.
Summarise the phase goal, the tasks left, and the break-it experiment in ≤15 lines.
Propose the next smallest step (files + tests). Wait for my go-ahead.
```

**Learn a pattern before building it**
```
/plan Explain <pattern> as it applies to OUR codebase (not generically):
the problem it solves here, the failure we will see without it, 2 alternative designs, and the trade-offs.
Then propose the implementation plan for this phase. Don't write code yet.
```

**Build a step (default)**
```
MODE: BUILD. Implement the approved step. Run make test and make lint and show me the output.
Then walk me through the key lines and the failure paths they handle.
```

**Run the break-it experiment**
```
Set up the break-it experiment for phase N exactly as described in the roadmap.
Implement it as a failing test and/or a pattern toggle (e.g. OUTBOX_ENABLED=false).
Run it and show me the output that proves the failure.
```

**Review my code (after a LEARNER-WRITES stub)**
```
Review my implementation in @services/<svc>/... against the pattern.
Point out correctness bugs first (concurrency, idempotency, failure paths), then design issues.
Don't rewrite it. Give hints and let me fix it.
```

**Close a phase**
```
Close phase N: run make clean && make up && make test && make e2e && make lint && make demo-N,
check every acceptance criterion with evidence (show the command output),
draft the ADR from docs/adr/0000-template.md, update docs/PROGRESS.md
(including the 3-line session summary), and give me the git commands to commit and tag phase-N-done.
```

**End any session**
```
Update the "Last session summary" in docs/PROGRESS.md (3 lines: done / next / open questions).
```

## Useful Claude Code features
The feature names below come from the current Claude Code docs. Run `/help` to confirm what your version supports.

- `/plan`: plan mode. Claude proposes a plan you can review and edit before any file changes.
- `@file` mentions and editor selections: attach exact code as context (`Alt+K` / `Option+K` inserts a reference to the selection).
- Checkpoints / `/rewind`: undo Claude's file edits back to an earlier message.
- `/context`: check that `CLAUDE.md` and `docs/PROGRESS.md` are loaded, and how full the context is.
- `/compact`: summarise a long conversation to free up context.
- `/clear`: start fresh. Recommended at the start of each new task; `docs/PROGRESS.md` carries continuity.
- `/memory`: edit `CLAUDE.md` files.

## Habits that make this work
1. **One task per conversation.** Clear often; the docs hold the state, not the chat history.
2. **Commit before each Claude step** (`git add -A && git commit -m "wip: before <step>"`). Checkpoints are a convenience, not a substitute for git.
3. **Always see it run.** Don't accept "this should work". Ask Claude to run the test or demo and show the output.
4. **Optional deeper learning:** use `MODE: GUIDED` for the core logic of the retry decorator, circuit breaker, outbox
   relay, idempotent consumer, saga orchestrator, and event folding. The tests are written first, so you know when
   you're done.
5. **Keep the parking lot** in `docs/PROGRESS.md` for ideas that belong to later phases.
6. **Update `CLAUDE.md`** only for durable rules and commands. Keep it under ~200 lines.
