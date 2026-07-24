# Joern graph-analysis requirements

Joern is authoritative for graph-sensitive claims about control flow, reachability,
call relationships, control dependencies, dominance, post-dominance, data flow, and
state-machine behavior. Manual source reading is not a replacement for required Joern
analysis.

Use Joern before and after edits involving branches, loops, state transitions, dispatch,
error handling, resource cleanup, authentication, authorization, input validation,
functions with multiple meaningful execution paths, callers or callees, reachability,
or source-to-sink data flow.

Required workflow:

1. Run `scripts/joern-snapshot baseline` before editing.
2. Identify affected methods and paths with `joern-agent` or the `joern_*` MCP tools.
3. Make the smallest appropriate change.
4. Repeat the same focused Joern queries.
5. Run `scripts/joern-snapshot post`.
6. Run `scripts/joern-compare`.
7. Run `scripts/joern-check`, tests, formatting, linting, type checking, and security checks.
8. Report the exact Joern commands or MCP tools used.
9. Report graph-derived findings and limitations.

Disclose unsupported language features, incomplete CPGs, failed or timed-out queries,
uncertain results, and possible frontend/data-flow semantic gaps. Never present an
unverified graph claim as certain.
