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

## Delivery cadence
- Lessons delivered **one at a time, on demand**. User asks ("next lesson" or a
  specific topic / detour); I author it, commit, push; Pages auto-deploys.
- Before writing lesson N+1, check: did they engage with lesson N's recall check or
  ask questions? Use that to set the difficulty and whether to write a learning record.
- Module 1 planned order is in `index.html` (2 control node → 3 inventory →
  4 playbook → 5 variables → 6 role anatomy → 7 modules/idempotency → 8 handlers →
  9 templates → 10 vault → 11 running & debugging). Deviate if their questions pull elsewhere.

## Session log
- 2026-09-07: workspace created. Mission set. Lesson 0001 (What is Ansible) authored.
  GitHub Pages via Actions workflow (publishes learn/ as site root). Cadence set to
  one-lesson-on-demand.
