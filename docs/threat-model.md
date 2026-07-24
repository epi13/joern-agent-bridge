# Threat model

## Assets and trust boundaries

Assets include private source, user credentials, the workstation, Codex configuration,
and integrity of graph evidence. Untrusted inputs include repository names and content,
MCP arguments, Joern output, and generated graph files. Trusted code includes the
installed signed/digested package, fixed Joern scripts, and reviewed hooks.

## Threats and controls

- Command injection: no shell interpolation; absolute executable and argument arrays.
- Path escape: canonicalization, approved-root checks, and symlink-escape rejection.
- Resource exhaustion: time, result, node, depth, path, and captured-output bounds;
  process-group termination; no default whole-graph response.
- Cache races or poisoning: content addressing, version/config keys, per-key locking,
  temporary output and atomic replacement.
- Secret leakage: small environment allowlist, no credential logging, ignored caches,
  no network MCP listener.
- Stale evidence: content and diff hashes verified at Stop time.
- Hook recursion: `stop_hook_active` changes repeated rejection into a visible,
  non-recursive warning.

Residual risks include vulnerabilities in Joern/JVM/frontends, malicious compiler
inputs, high memory use, imprecise graphs, platform-specific process behavior, and a
local user tampering with their own executable or validation record and source
together. This is a development guardrail, not a hostile-host security boundary.
