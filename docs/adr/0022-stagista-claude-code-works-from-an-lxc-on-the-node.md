# 0022 — stagista: Claude Code works from an LXC on the node

Applies to: the `stagista_lxc` role and the `stagista_*` variables. The README's
"stagista" section covers how to use it.

**Decision.** Infrastructure work happens in an LXC on the node, so a session
doesn't depend on a laptop staying awake. stagista reaches `pve` over SSH as
root, as a laptop would. That makes it a matter of tidiness and
reproducibility, **not a security boundary**. The vault password is never
stored there: playbooks are still run by a person typing it.

**Rules that follow from it.**
- **Sudo:** passwordless inside the container. The agent already holds root
  SSH to the host, so a sudo password would guard nothing.
- **SSH keys:** one per destination (`pve`, GitHub, the Hetzner server),
  generated inside the container and never copied in, so each can be revoked
  on its own. The GitHub key is an account key, because stagista works on
  every personal repo.
- **Git:** the repo is cloned over HTTPS (it's public, so no key is needed to
  read it). Pushes go over SSH with that GitHub key.
- **Ansible:** installed with `pipx`, not Debian's package. Debian's Ansible
  lags, and the playbooks are written against the current release, as run from
  a laptop.
- **Repos** live in `~/code`, not the home folder. Claude Code never remembers
  trust for a home folder, and a Remote Control server has no terminal to ask
  on.
- **Remote Control:** one server per project folder
  (`claude-remote-control@<folder>`), so each shows up on its own when starting
  a session from claude.ai/code or the Claude app.
  - Each is started only once Claude is signed in and that folder trusted.
    Both are steps for a person at the terminal; before them, the server would
    only crash-loop.
  - No idle session is pre-created per server: three would sit in RAM for
    nothing.
- **Locale:** `C.UTF-8`. The template ships `LANG=C`, and under a non-UTF-8
  locale tmux shows every non-ASCII character (Claude Code's whole interface)
  as `_`.
- **sshd:** Debian 13 starts sshd per connection from `ssh.socket`, and each
  one reads the config afresh. Only a long-running `ssh.service` needs a
  reload.
- **tmux:**
  - Dots in session names become underscores up front
    (`aleromano.com` → `aleromano_com`), because tmux would convert them anyway
    and lookups must match.
  - An unknown `$TERM` (such as `xterm-ghostty`) falls back to
    `xterm-256color`, instead of tmux refusing the login.
  - The clipboard reaches the Mac over SSH through OSC 52.
