# 0003 — Ansible only; no Terraform/OpenTofu

Infrastructure (the VM and LXCs) and configuration are both done in Ansible, rather
than Terraform for provisioning + Ansible for config. For a single local node the
drift-detection benefit of Terraform is marginal, and one tool to learn beats two.
Ansible tasks drive the native Proxmox CLIs (`pct`, `qm`) and `docker compose`
directly with idempotency guards — no API token dance, and the learner sees the
real commands. Consequence: no declarative state file; "does reality match the
repo?" is answered by re-running the playbook.
