# Joern query guide

Start with `methods` or `search-methods`, then use exact method names for CFG,
callers, callees, controls, dominance, and post-dominance. Use a node ID returned by
the same current CPG for neighbor queries. Bound call paths by depth and count.

Data flow treats parameters of methods matching the source regex as sources and
arguments to calls matching the sink regex as sinks. Keep both expressions narrow.
Joern data-flow semantics and type recovery affect results; a missing path is not
proof of absence.

`export` supports `ast`, `cfg`, `cdg`, `ddg`, `pdg`, `cpg`, and `all`. Exports are
artifacts, not normal LLM responses. Render DOT with `dot -Tsvg input.dot -o output.svg`.

All query results include exact Joern version, operation, limits, elapsed time,
warnings, and CPG path alongside Joern node properties such as ID, label, file, line,
column, method, and code when that frontend provides them.
