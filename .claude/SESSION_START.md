# SESSION_START — paste this into a new chat to resume the project

> Copy everything inside the code block below and send it as your first message in a new session.
> It stays valid over time because it points at `.claude/HANDOFF.md` (which carries the current state)
> rather than hard-coding details. Keep `HANDOFF.md` up to date; keep this file stable.

```
You are resuming work on this repository (TradingView MCP server + the Saudi Main Market wave-screening
system W1/W2/W3 + tracker + a Python research/backtesting platform). Before doing ANYTHING else, read
these files in full (repo-relative paths) and run the git commands, to reconstruct context:

1. .claude/HANDOFF.md                         — START HERE: current state, decisions, findings, open items
2. research/spec/TESTING.md                   — the official / conformance / experimental conventions (MUST follow)
3. research/ARCHITECTURE.md                   — the research platform design + rationale
4. research/spec/rules.yaml                    — canonical W1/W2/W3 rule definitions (single source of truth)
5. .claude/commands/saudi-stage2.md           — W1 live command spec
6. .claude/commands/saudi-wave2.md            — W2 live command spec
7. .claude/commands/saudi-wave3.md            — W3 live command spec
8. .claude/commands/saudi-track.md            — tracker command spec
9. run: git status --short  AND  git log --oneline -15
                                             — reconstruct working-tree + commit context: uncommitted/untracked
                                               (WIP) changes AND recent history (HEAD = latest; do not assume)

Then follow these working rules for the whole session:

A. OFFICIAL METHODOLOGY lives ONLY in research/spec/rules.yaml + the live scripts
   (.claude/scripts/saudi-stage2.js, saudi-wave2.js) + the command docs, and is PARITY-LOCKED by
   research/spec/conformance/methodology_parity.py. The live JS and rules.yaml must never drift.

B. EXPERIMENTS live in research/experiments/ and use runtime overrides only (params_overrides) and/or
   clearly-labelled observable candidate filters. They MUST NOT edit any official file. Their outputs are
   HYPOTHESES, never "the methodology." Do not present experimental results as official.

C. PROMOTION (experiment -> official) = edit research/spec/rules.yaml + the JS + the docs + the golden
   vectors together (the parity gate then enforces consistency), and FORWARD-BACKTEST before trusting.
   Show me the evidence before promoting any methodology change; let me make the call.

D. Discipline: architecture/spec first, then tests/golden fixtures, then implementation, then proof via
   conformance/CI, before committing. Keep increments small, self-contained, and fully validated. At the
   end of each increment: what's done, what remains, and why the next step.

E. NEVER commit market data (research/panel/*.parquet, research/ingest/raw/) or package-lock.json.
   .claude/ is git-ignored — force-add specific files (git add -f) when they must be tracked.

F. Push with:  git push mine feat/saudi-stage2-screen   (SSH deploy key ~/.ssh/mine_tadawul is already
   wired via core.sshCommand; the `mine` remote is the git@github.com SSH URL). Commit/push only when I ask.

G. Use full repo-relative paths when referring to files. Verify facts against the current code before
   asserting them (this handoff is point-in-time).

Confirm you've read the files above and summarise the current state + the top open item, then wait for my
instruction.
```
