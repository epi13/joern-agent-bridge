# C demonstration fixture

This small program intentionally contains a harmless unsanitized path from `argv[1]`
through `process_request` to `unsafe_sink`, alongside validation, a loop, nested control
flow, normal and error exits, and caller/callee relationships.

```bash
joern-agent parse examples/c-demo --language c
joern-agent methods examples/c-demo --json
joern-agent cfg examples/c-demo --method process_request --json
joern-agent callers examples/c-demo --method process_request --json
joern-agent callees examples/c-demo --method process_request --json
joern-agent controls examples/c-demo --method process_request --json
joern-agent call-paths examples/c-demo --source main --sink unsafe_sink --json
joern-agent dataflow examples/c-demo --source process_request --sink unsafe_sink \
  --max-depth 20 --max-paths 10 --json
```

The repository's `scripts/demo-workflow` copies the fixture to a temporary directory,
creates a real baseline snapshot, applies the documented safety edit, creates the
post-edit snapshot, compares them, and preserves only sanitized result examples.
