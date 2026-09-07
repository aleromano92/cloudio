# Mission: Own the cloudio home-server stack

## Why
I'm building a home server (Proxmox + Ansible + LXC/VM, Home Assistant, UniFi,
media stack) on an old Vaio laptop, on purpose, as a hands-on learning project.
I want to understand every concept the repo applies — starting with Ansible from
zero — so I can extend, debug, and rebuild it myself instead of copy-pasting, and
carry the skills to a bigger server later.

## Success looks like
- I can read any file in `ansible/` and explain what each line does and why.
- I can add a new service (a new role + LXC) to the playbook unaided.
- I can debug a failed run: read the error, find the task, fix the variable or module call.
- I can explain Ansible's model — control node, inventory, playbook, role, module,
  idempotency — from memory.
- Later: the same depth for Proxmox/LXC, systemd timers, restic, Tailscale, and the
  flat-network design.

## Constraints
- No Proxmox hardware yet → lessons are read-the-repo + concept quizzes until the box exists.
- Short lessons. Delivered as HTML in `learn/`, committed to the public GitHub repo.
- My wife may follow along, so prerequisites stay explicit.
- Ansible first and deeply, then the rest of the stack.
- I'm already comfortable with Docker/compose, the shell, and git.

## Out of scope (for now)
- Ansible features cloudio doesn't use: dynamic inventory, AWX/Automation Controller,
  Molecule, multi-host fleets, CI pipelines.
- Terraform / OpenTofu (ADR-0003 rules it out).
- Kubernetes, Docker Swarm.
