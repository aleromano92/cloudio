# 0003 — Ansible only; no Terraform/OpenTofu

Infrastructure (the VM and LXCs) and configuration are both done in Ansible, using
the community.general Proxmox modules, rather than Terraform for provisioning +
Ansible for config. For a single node the drift-detection benefit of Terraform is
marginal, and one tool to learn beats two. Consequence: no declarative state file;
"does reality match the repo?" is answered by re-running the playbook.
