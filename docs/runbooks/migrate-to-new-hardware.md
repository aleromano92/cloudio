# Runbook — Migrate to new hardware

> **Stub.** Flesh this out after the first successful end-to-end build. Assumes the
> target is an **x86** machine (Proxmox does not run on Apple Silicon).

Estimated time for a like-for-like x86 box: **~2.5–4 hours, mostly waiting on
downloads** — *provided backups are current*.

## Steps

1. **Install Proxmox VE** on the new box, static IP `.10` (Phase 0, step 1).
2. **Update `ansible/group_vars/all/vars.yml`**: new node IP if changed, external
   drive UUID, any MAC-derived values.
3. From the laptop: `ssh-copy-id root@<new-ip>`.
4. `ansible-playbook site.yml --ask-vault-pass` — recreates the HAOS VM + both
   LXCs, installs Docker/UniFi, pulls images.
5. **Re-attach the same external USB media drive.** Media does not move — zero copy.
6. **Restore state** (see `restore-from-backup.md`):
   - Home Assistant: restore the HA backup `.tar`.
   - `media` LXC: `restic restore` `/opt/appdata/*`, then `docker compose up -d`.
   - `unifi` LXC: restore the `.unf`, re-adopt APs.
7. **Re-auth Tailscale** on the new node; fix DHCP reservations for new MACs.
8. **Verify** every service, then decommission the old box.

## Notes

- The playbook is the reproducible part; state always comes from backups regardless
  of target hardware (ADR-0002).
- If the move is motivated by needing Frigate or a heavier personal cloud, size the
  new box accordingly (more cores, HEVC-capable iGPU, more RAM, ideally 2 disks).
