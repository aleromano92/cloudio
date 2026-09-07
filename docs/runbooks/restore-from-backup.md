# Runbook — Restore from backup

> **Stub.** Flesh this out once the `proxmox_base` backup role and the first real
> backups exist. See README "What lives in git" for the backup design.

## What is backed up

| Source | What | Where |
|---|---|---|
| `media` LXC | `/opt/appdata/*` (arr SQLite DBs, qBittorrent config, Prowlarr) + weekly full `vzdump` | Local backup partition + `restic` → Hetzner Storage Box |
| `unifi` LXC | UniFi auto-backup `.unf` + weekly full `vzdump` | Local backup partition + `restic` → Hetzner |
| `homeassistant` VM | HA native backup `.tar` + weekly full `vzdump` | Local backup partition + `restic` → Hetzner |
| Proxmox host | `/etc/pve`, `/etc/network/interfaces`, `/etc/modprobe.d`, fstab/mount units | `restic` → Hetzner |
| Media library | *nothing — disposable* | — |

Retention: 7 daily / 4 weekly. `restic` password is in `ansible/group_vars/all/vault.yml`.

Driven by `/usr/local/sbin/cloudio-nightly-backup.sh` on `pve` (systemd timer
`cloudio-backup.timer`). Repo + password come from `/etc/cloudio-backup.env`; the
Storage Box connection uses `/root/.ssh/config` (port 23, key auth). To browse
snapshots manually: `set -a; . /etc/cloudio-backup.env; set +a; restic snapshots`.

## Restore a single service (media stack)

1. TODO: stop the affected container.
2. TODO: `restic restore` the relevant `/opt/appdata/<svc>` snapshot.
3. TODO: `docker compose up -d`, verify.

## Restore a whole guest from `vzdump`

1. TODO: `qmrestore` / `pct restore` from the local partition or a `restic`-restored dump.

## Restore Home Assistant

1. TODO: bring up a fresh HAOS VM via the playbook.
2. TODO: upload the HA backup `.tar` in onboarding, restore.

## Restore UniFi

1. TODO: bring up a fresh `unifi` LXC via the playbook.
2. TODO: restore the `.unf` file in the setup wizard.
3. TODO: re-adopt the APs (set-inform / factory adopt if needed).

## Verify

- TODO: checklist per service.
