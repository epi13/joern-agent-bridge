# Contributing

Create an issue for material design changes. Use a focused branch, preserve path
confinement and bounded-query guarantees, and never replace a real Joern integration
test with a mock. Run formatting, linting, strict type checking, unit and integration
tests, package build, and dependency audit before proposing a change.

Graph-sensitive changes must follow the root `AGENTS.md` baseline/post workflow.
Commits must not contain CPG databases, private source snapshots, credentials, or
unbounded graph exports. By contributing, you agree that your work is licensed under
Apache-2.0 and to follow the Code of Conduct.
