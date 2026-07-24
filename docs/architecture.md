# Architecture

`JoernService` is the application boundary shared by the CLI and MCP server. It
validates paths, discovers a pinned Joern installation, asks `CpgWorkspace` for an
immutable content-addressed CPG, and delegates fixed operations to `QueryRunner`.
`process.run_process` supplies the only general subprocess primitive.

The cache key covers resolved source root, source bytes, frontend, configuration, and
Joern version. Per-key file locks serialize writers. A completed entry is immutable,
so concurrent readers require no write lock. Failed temporary CPGs are removed.

Joern's noninteractive Scala script contains an operation allowlist. Values reach it
only as command arguments; none are interpreted as shell or Scala source. Results are
emitted behind one marker as JSON and rejected unless exactly one valid payload exists.
Exports use Joern's official exporter and return paths instead of graph contents.

Snapshots and hooks are separate modules. The Stop hook independently recomputes the
source and relevant-diff hashes and accepts only a successful record containing both
baseline and post states.
