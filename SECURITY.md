# Security policy

Report vulnerabilities privately through GitHub's security advisory interface for
`epi13/joern-agent-bridge`. Do not include credentials, private source, or harmful
payloads in public issues. Supported security fixes target the latest release on
`main`; older versions receive fixes at maintainer discretion.

This project executes Joern locally. Treat analyzed repositories as untrusted input,
keep the MCP transport on STDIO, review Codex hook trust, use explicit approved roots,
and do not expose Joern server mode to a network. Static-analysis results may be
incomplete and must not be the sole basis for high-impact security decisions.
