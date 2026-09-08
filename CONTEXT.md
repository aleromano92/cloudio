# Cloudio — Home Server

A single-node home server built on a repurposed Sony Vaio laptop running Proxmox VE.
The repo is the reproducible recipe: from a fresh Proxmox install, cloning it and
running one Ansible playbook rebuilds every service. Also a deliberate learning
project (Proxmox, LXC, Ansible, networking).

## Language

**Node**:
The single physical machine (the Vaio) running Proxmox VE. Hostname `pve`.
_Avoid_: server (ambiguous — the whole project is "the server"), box.

**Phase 0**:
The manual, one-time bootstrap done by hand before Ansible can run: install
Proxmox, set a static IP, authorise the laptop's SSH key, prepare variables.
_Avoid_: setup, install.

**v1**:
The initial buildable scope: media stack + Home Assistant + UniFi controller on a
flat network. Explicitly excludes VLANs, the personal cloud, and Frigate.
_Avoid_: MVP, phase 1 (reserve "Phase N" for later stages only).

**Media stack**:
The set of Docker services — Jellyfin, Sonarr, Radarr, Lidarr, Prowlarr,
qBittorrent — running together in the `media` LXC via docker-compose.
_Avoid_: arr stack (that's only a subset), Jellyfin (one service of many).

**Config**:
Declarative definitions the repo owns and Ansible applies: playbooks, roles, the
compose file, hand-written base files. Losing the node loses none of this.
_Avoid_: settings.

**State**:
Runtime data that lives only on the node and changes as services run: HA's config
after UI edits, the *arr SQLite databases, qBittorrent data, UniFi's MongoDB.
Never in git; protected by backups.
_Avoid_: data (too broad), config.

**Disposable data**:
The media library. Re-acquirable from original sources. Gets no backup.
_Avoid_: temporary (it's kept indefinitely, just not protected).

**Precious data**:
Personal documents and photos, destined for the future personal-cloud phase.
Requires real redundancy. Does not exist on the node yet.
_Avoid_: important data.

**Control node**:
The laptop. Runs Ansible against the node over SSH. Never itself provisioned by
this repo.
_Avoid_: admin machine.

**OWN gateway** (in the smart-home context):
A BTicino/Legrand gateway that speaks **OpenWebNet** (F454, F459/MyHOMEServer1,
MH201, or F461) bridging the wired MyHOME SCS bus to the LAN, so Home Assistant
can see bus devices. Note: the F460 already installed here is *not* one — it is
Home + Control only.
_Avoid_: IP gateway (ambiguous — the F460 is an "IP gateway" but not an OWN one),
bridge, hub.

**Off-site backup**:
The `restic` repository on the Hetzner Storage Box. The only copy of State that
survives loss of the house.
_Avoid_: cloud backup.
