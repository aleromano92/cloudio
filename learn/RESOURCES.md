# cloudio stack — Learning Resources

Knowledge is drawn from here, not from memory. Wisdom comes from the communities below.

## Knowledge

### Ansible (primary)
- [Introduction to Ansible — Ansible Community Documentation](https://docs.ansible.com/projects/ansible/latest/getting_started/introduction.html)
  The canonical "what it is": agentless, over SSH, declarative desired state, idempotence, playbooks. Use for: precise definitions.
- [Getting started with Ansible](https://docs.ansible.com/projects/ansible/latest/getting_started/index.html)
  Control node / inventory / managed nodes; first inventory; first playbook. Use for: the mental model and first commands.
- [Building an inventory](https://docs.ansible.com/projects/ansible/latest/getting_started/get_started_inventory.html)
  INI vs YAML inventory, groups, `group_vars`. Use for: the `inventory.yml` lesson.
- [Roles — Playbook guide](https://docs.ansible.com/ansible/latest/playbook_guide/playbooks_reuse_roles.html)
  Role layout (`tasks/ handlers/ templates/ files/ defaults/`), the role search path. Use for: the four-roles lessons.
- [Using variables](https://docs.ansible.com/ansible/latest/playbook_guide/playbooks_variables.html)
  Variable precedence, `group_vars/all`, templating. Use for: the `group_vars` lesson.
- [Encrypting content with Ansible Vault](https://docs.ansible.com/ansible/latest/vault_guide/index.html)
  Use for: the `vault.yml` lesson.
- [Templating (Jinja2)](https://docs.ansible.com/ansible/latest/playbook_guide/playbooks_templating.html)
  Use for: the `.j2` template lessons (restic script, ssh config, systemd units).
- [Error handling — `changed_when`, `failed_when`, `creates`, handlers](https://docs.ansible.com/ansible/latest/playbook_guide/playbooks_error_handling.html)
  Use for: the idempotency-guard lessons (the `command:`/`shell:` tasks all over this repo).
- [Module index: `ansible.builtin`](https://docs.ansible.com/ansible/latest/collections/ansible/builtin/index.html)
  Use for: looking up `apt`, `copy`, `template`, `get_url`, `systemd`, `command`, `replace`, `file`.

### The rest of the stack (to gather later)
- Proxmox VE wiki + `man pct` / `man qm` — the LXC/VM CLIs the roles call.
- systemd `man systemd.timer` / `systemd.service` — the backup schedule.
- restic docs (restic.readthedocs.io) — the off-site backup tool.
- Tailscale docs (tailscale.com/kb) — the mesh VPN + subnet router.

## Wisdom (Communities)
- [Ansible community forum](https://forum.ansible.com/) — official, well-moderated. Use for: "is this idiomatic?"
- [r/ansible](https://www.reddit.com/r/ansible/) — playbook/role critique.
- [r/Proxmox](https://www.reddit.com/r/Proxmox/) and [r/homelab](https://www.reddit.com/r/homelab/) — this exact class of build.
- [Home Assistant Community — Legrand/Bticino MyHome thread](https://community.home-assistant.io/t/legrand-bticino-myhome/229337) — OpenWebNet integration, gateways, real configs.

## Gaps
- No primary source yet on **unprivileged LXC + Docker nesting** caveats — needed before the `media_lxc` deep-dive.
- No chosen reference for **Jinja2 filters** used in the repo (`default`, `regex_replace`, `join`) — gather with the templating lesson.
