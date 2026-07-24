# Codex integration

The project config starts `joern-agent-mcp` over STDIO, marks it required, enables
hooks, and uses 30-second startup and 600-second tool timeouts. The user config uses
the same PATH command but `required = false`, so unrelated repositories are not
blocked by Joern.

Codex project `.codex` layers load only for trusted repositories. Non-managed hooks
also require definition-level review; use `/hooks` in a fresh session. A currently
running Codex process does not reload newly installed MCP executables or config.

Protocol verification uses an MCP initialization request, `tools/list`, and a real
fixture tool call. `codex mcp list` verifies merged configuration.

The SessionStart hook checks availability and config only. The Stop hook ignores
documentation-only edits and rejects missing, failed, malformed, or stale graph
evidence. `stop_hook_active` prevents an infinite continuation loop while retaining a
visible warning.
