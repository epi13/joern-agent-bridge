# Joern tooling

The runtime noninteractive script is packaged at
`src/joern_agent_bridge/joern/query.sc` so wheel installations can resolve it with
`importlib.resources`. Keep Joern-version installation helpers under `scripts/`.
This directory is reserved for developer-side query inspection or future fixed
Joern utilities; generated CPGs and exports do not belong here.
