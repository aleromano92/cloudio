# Cloudio — Home Server

A single-node home server built on a repurposed Sony Vaio laptop running **Proxmox VE**.

This repo is the reproducible recipe: from a fresh Proxmox install, cloning it and
running one Ansible playbook rebuilds every service. It is also a deliberate
learning project — Proxmox, LXC, Ansible, and home networking.

> Status: **first draft.** Docs, decisions, and all four Ansible roles are written
> but **untested against real hardware** — expect to refine them during the actual
> build. See the roadmap below.

---

## Hardware

| Part | Spec | Notes |
|---|---|---|
| Machine | Sony Vaio SVF153A1YM | Repurposed 2013 laptop |
| CPU | Intel Core i7-4500U (Haswell, 2c/4t) | H.264 hardware transcode via Quick Sync; **no HEVC hardware decode** |
| RAM | **16 GB** DDR3L-1600 SO-DIMM (2×8 GB) | Upgraded from 8 GB; 16 GB is the ceiling |
| GPU | Intel HD 4400 + GeForce GT 740M | dGPU is blacklisted (unused, saves power/heat) |
| System disk | 256 GB SSD | Proxmox + configs + container rootfs |
| Media disk | External 3.5" USB 3.0 desktop drive (~8 TB, ext4) | Media library only — **not backed up** (disposable) |

Frigate / local NVR is **out of scope** on this hardware. Camera recording stays on
the Reolink NVR's own disk.

---

## Architecture

One Proxmox node (`pve`) hosting:

| Guest | Type | Purpose |
|---|---|---|
| `homeassistant` | VM (HAOS, 2 GB / 2 vCPU) | Home Assistant OS with Supervisor + add-ons |
| `media` | LXC (Docker) | Jellyfin, Sonarr, Radarr, Lidarr, Prowlarr, qBittorrent via `docker-compose` |
| `unifi` | LXC (native) | UniFi Network Application (controller for the U7 Pro Wall APs) |

Room is reserved for a 4th guest later: the personal-cloud phase (documents + photos, with real redundancy).

### Addressing

Static IPs on the infrastructure; DHCP reservations for everything else.

| Host | IP (last octet) |
|---|---|
| `pve` | `.10` |
| `homeassistant` | `.11` |
| `media` | `.12` |
| `unifi` | `.13` |

Names resolve via Tailscale MagicDNS and a local hosts/DNS entry. No dedicated DNS server in v1.

---

## Repo layout

```
cloudio/
├── README.md                 # this file
├── CONTEXT.md                 # project glossary / ubiquitous language
├── docs/
│   ├── adr/                   # architecture decision records
│   ├── network-topology.md    # flat-now / VLAN-later plan
│   └── runbooks/              # restore-from-backup, migrate-to-new-hardware
├── ansible/
│   ├── ansible.cfg
│   ├── inventory.yml           # one host: pve
│   ├── site.yml                # runs the four roles
│   ├── requirements.yml        # ansible.posix, community.general
│   ├── group_vars/all/
│   │   ├── vars.yml            # everything you set (CHANGE-ME markers)
│   │   ├── vault.yml.example   # template for the encrypted secrets file
│   │   └── vault.yml           # you create this: ansible-vault encrypted
│   └── roles/
│       ├── proxmox_base/       # no-sub repo, packages, dGPU blacklist, USB mount,
│       │                       #   Tailscale, restic + nightly vzdump timer
│       ├── haos_vm/            # download HAOS image, qm create/import, start
│       ├── media_lxc/          # pct create, install Docker, deploy the compose stack
│       └── unifi_lxc/          # pct create, install UniFi (MongoDB 7 + OpenJDK 17)
└── media-stack/
    ├── docker-compose.yaml     # Linux paths; PUID/PGID/TZ/paths via .env
    └── .env.example
```

---

## Phase 0 — manual bootstrap (one time)

Everything after this is `ansible-playbook site.yml` from the laptop.

1. **Install Proxmox VE** on the Vaio from a USB stick. Give it a **static IP** on the LAN (`.10`).
2. **Format the external drive ext4**, then note its UUID (`blkid /dev/sdX1`). Mount
   your local backup disk/partition at `/mnt/backup`.
3. From the laptop: `ssh-copy-id root@<pve-ip>` so Ansible can log in without a password.
4. **Install Ansible on the laptop**: `pipx install ansible` (or `brew install ansible`).
5. **Clone this repo**, then:
   ```bash
   cd ansible
   ansible-galaxy collection install -r requirements.yml
   cp group_vars/all/vault.yml.example group_vars/all/vault.yml
   $EDITOR group_vars/all/vault.yml          # Tailscale auth key, restic password
   ansible-vault encrypt group_vars/all/vault.yml
   $EDITOR group_vars/all/vars.yml           # fill every CHANGE-ME (pve_ip, drive UUID,
                                             #   Storage Box user/host, HAOS version)
   ```
6. On first Storage Box use, the `proxmox_base` role prints an SSH public key to
   install on the box (`ssh-copy-id -p23 uXXXXXX@uXXXXXX.your-storagebox.de`), then
   re-run so `restic init` succeeds.

Automating the Proxmox install itself (answer file) is a possible later step, not v1.

---

## How to run

After Phase 0:

```bash
cd ansible
ansible-playbook site.yml --ask-vault-pass
```

Useful subsets:

```bash
ansible-playbook site.yml --ask-vault-pass --tags base       # just the host
ansible-playbook site.yml --ask-vault-pass --tags haos       # just the HA VM
ansible-playbook site.yml --ask-vault-pass --tags media
ansible-playbook site.yml --ask-vault-pass --tags unifi
ansible-playbook site.yml --ask-vault-pass --check           # dry run
```

Re-running is safe (idempotent). Ansible drives the native `pct` / `qm` /
`docker compose` CLIs directly — there is no Terraform and no state file; "does
reality match the repo?" is answered by re-running the playbook (see ADR-0003).

### Before the external drives arrive

`base`, `haos`, and `unifi` run fully without any external storage. Run those:

```bash
ansible-playbook site.yml --ask-vault-pass --tags base,haos,unifi
```

Hold `--tags media` until the media drive is in (`media_disk_uuid` set), and keep
`backups_enabled: false` until the local backup disk + Storage Box exist. Then:

```bash
# media drive fitted, formatted ext4, UUID in vars.yml:
ansible-playbook site.yml --ask-vault-pass --tags storage,media
# backup disk mounted at /mnt/backup, Storage Box created, backups_enabled: true:
ansible-playbook site.yml --ask-vault-pass --tags backup
```

### Hardware transcoding

Jellyfin hardware transcoding (Intel Quick Sync — **H.264 only** on this CPU, no
HEVC) needs the render node (`/dev/dri/renderD128`) exposed to the unprivileged
`media` LXC: add `lxc.cgroup2.devices.allow` + `lxc.mount.entry` lines to
`/etc/pve/lxc/112.conf`, then uncomment the `devices:` block in
`media-stack/docker-compose.yaml`. Left disabled in this draft — direct play and
software transcode work without it. TODO: fold this into the `media_lxc` role.

---

## What lives in git, and what does not

- **In git:** how to build the node — playbooks, roles, the compose file, hand-written base config.
- **Not in git:** runtime *state* — Home Assistant's config after UI edits, the *arr
  SQLite databases, qBittorrent data, UniFi's MongoDB. That is protected by
  **backups**, not version control (see ADR-0002).

**Backups:** nightly `vzdump` of the LXCs + HA backups to a local partition, plus a
nightly `restic` push to a Hetzner Storage Box (the only off-site copy). Media is
not backed up.

---

## Remote access

Tailscale on the node, the laptop, and phones. **Nothing is port-forwarded** on the
router. The public IP is publicly reachable but **dynamic** (rotates every few
days) — irrelevant here, since Tailscale doesn't use it and needs no dynamic DNS
(see ADR-0006).

---

## Roadmap

**v1 (current):** media stack + Home Assistant + UniFi controller, flat network, Tailscale, backups.

**Later phases:**
- Smart-home: integrate the wired **BTicino MyHOME** bus into Home Assistant via
  the HACS OpenWebNet integration. **BLOCKED (2026-09-10):** installer fitted an
  **F460** (no OpenWebNet) without consulting; MyHOMEServer1 is EOL; F460 + F461
  is forbidden by BTicino. Resolution in progress — likely **replace F460 with
  F461** (HA-only, no BTicino app). See ADR-0007. Whatever lands, get from the
  installer: OpenWebNet enabled + HMAC password, a static IP for the gateway, and
  the MyHOME_Suite project file.
- **Personal cloud** for documents + photos, with real redundancy.
- **Network segmentation** — IoT/camera VLAN. Needs a real L3 gateway (UniFi
  gateway or dedicated OPNsense box — **not** the Vaio). See `docs/network-topology.md`.
- **Frigate** — only on a future, more capable box (or with a Coral).
- Automated Proxmox install via answer file.

---

## Background

- Project glossary: [`CONTEXT.md`](./CONTEXT.md)
- Why things are the way they are: [`docs/adr/`](./docs/adr/)
