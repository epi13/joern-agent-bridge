# Installation log

This log records project-relevant changes only. Credentials, tokens, unrelated
configuration, and unnecessary machine details are omitted.

## 2026-07-24

1. Inspected Fedora, architecture, memory/disk capacity, shell, Java, Python, Git,
   Codex, GitHub CLI authentication state, Podman, Graphviz, Joern, PATH, Codex
   configuration/instructions/hooks, and Git identity.
2. Confirmed `~/.local/bin` was already on PATH, so no shell startup file changed.
3. Installed missing Fedora packages with `dnf`: `graphviz`,
   `java-25-openjdk-devel`, `python3-devel`, and `pipx`, plus their transaction
   dependencies. Existing Git, GitHub CLI, curl, jq, archive tools, compilers, make,
   Python, Java runtime, and Podman were retained.
4. Resolved official Joern release `v4.0.583`, downloaded and inspected
   `joern-install.sh`, and verified its GitHub SHA-256 digest. The installer was not
   executed because it does not verify the CLI archive.
5. Downloaded `joern-cli.zip` before extraction. Verified GitHub SHA-256
   `74e072163b7f1fc1a371a265ca6f1a94a54507eb20bb831babb288d40f4d278e`
   and Joern's published SHA-512
   `5eb2fb4b2011585d11cc7e5ea21af99afc66cee7535ff0a2724647952590c300a84afe23df3317d19667a55b8b5bac46b74172e63a687282753ec9f544314c3a`.
6. Extracted Joern to `~/.local/share/joern/v4.0.583` and linked user commands
   under `~/.local/bin`.
7. Verified Joern launch, C parsing, structured noninteractive JSON, CFG DOT export,
   and Graphviz SVG rendering on the included fixture.
8. Installed `joern-agent-bridge` 0.1.0 through pipx and verified all three PATH
   executables.
9. Backed up `~/.codex/config.toml` to
   `~/.codex/config.toml.bak-20260724T150758-0800`, merged the optional global MCP
   entry, created marked global Joern guidance, and validated TOML.
10. Verified `codex mcp list`, installed MCP initialization, `tools/list`, a real
    `joern_list_methods` call, SessionStart, and Stop rejection without evidence.

No SELinux, firewall, sudoers, privileged group, daemon, or network-service change
was made.
