# Teaching notes

## Preferences
- Lessons: short, HTML, in `learn/`, committed to the public GitHub repo. Browsable
  from `learn/index.html`.
- Delivery style: **read-the-repo + in-browser quizzes**. No local Ansible install
  yet (no Proxmox hardware). Revisit hands-on practice when the node is built.
- Curriculum order: Ansible (deep) → Proxmox/LXC → systemd timers + restic/backups
  → Tailscale/networking → Docker/media-stack specifics.
- Depth target: "own this repo." Don't chase Ansible features cloudio doesn't use.
- Wife may follow along → keep prerequisites explicit; don't assume prior Ansible.

## Known prior knowledge (as of setup)
- Comfortable: Docker & docker-compose, the shell, git, general sysadmin reasoning,
  reading YAML. Not new to tech.
- New to: Ansible, Proxmox, LXC, infrastructure-as-code, Jinja2, Ansible Vault.

## Mechanics
- Quiz answers must be roughly equal length with no formatting tells (teach-skill rule).
- Each lesson: one win, a primary source, a repo task, a recall check, a follow-up nudge.
- Viewing rendered HTML: open files locally, or enable GitHub Pages (Settings → Pages
  → deploy from `master`, `/` root) and browse at `…/learn/`.

## Session log
- 2026-09-07: workspace created. Mission set. Lesson 0001 (What is Ansible) authored.
