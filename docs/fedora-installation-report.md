# Fedora installation report

Date: 2026-07-24

- Fedora release: 44 (Forty Four), x86_64
- Memory available during inspection: approximately 19 GiB
- Project filesystem free space during inspection: approximately 117 GiB
- Shell: Bash
- Python: 3.14.6
- Git: 2.55.0
- Codex CLI: 0.144.6
- GitHub CLI: 2.94.0, authenticated through the system keyring
- Podman: 5.8.4
- Java: OpenJDK 25.0.3
- Graphviz: 14.1.4
- Joern: 4.0.583
- `~/.local/bin`: already on PATH; no shell startup change was required

Fedora packages installed solely/missing for this work:

- `graphviz`
- `java-25-openjdk-devel` (and transaction dependencies)
- `python3-devel`
- `pipx`

Joern release files were downloaded from the official `joernio/joern` v4.0.583
release. `joern-install.sh` had GitHub SHA-256
`790a4c7e0d99a71a101292189e6607c62b2e8aafd81f41df177ffc61dfde26cf`
and was inspected but not executed because it does not verify the CLI archive.
`joern-cli.zip` matched GitHub SHA-256
`74e072163b7f1fc1a371a265ca6f1a94a54507eb20bb831babb288d40f4d278e`
and the release's SHA-512 file before extraction.

No SELinux, firewall, sudoers, groups, daemons, or network listeners were changed.

## Uninstall

```bash
pipx uninstall joern-agent-bridge
rm -f ~/.local/bin/joern ~/.local/bin/joern-parse ~/.local/bin/joern-export \
  ~/.local/bin/joern-scan ~/.local/bin/joern-slice ~/.local/bin/joern-flow
rm -rf ~/.local/share/joern/v4.0.583 ~/.cache/joern/v4.0.583 \
  ~/.cache/joern-agent-bridge
sudo dnf remove graphviz java-25-openjdk-devel python3-devel pipx
```

Edit `~/.codex/config.toml` to remove only the marked
`[mcp_servers.joern]` section and edit `~/.codex/AGENTS.md` to remove only the
marked Joern guidance. Restore the timestamped backups recorded in the final report
if desired. No PATH section was added on this workstation; if one is added elsewhere,
remove only its clearly marked block from the shell startup file.
