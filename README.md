# Cloudio — Home Server

A single-node home server built on a repurposed Sony Vaio laptop running **Proxmox VE**.

This repo is the reproducible recipe: from a fresh Proxmox install, cloning it and
running one Ansible playbook rebuilds every service. It is also a deliberate
learning project — Proxmox, LXC, Ansible, and home networking.

> Status: **bootstrapping.** The docs and decisions are in place; the Ansible roles
> are being built incrementally. See the roadmap below.

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
├── ansible/                   # (built during the setup sessions)
│   ├── ansible.cfg
│   ├── inventory.yml
│   ├── site.yml
│   ├── requirements.yml
│   ├── group_vars/all/
│   │   ├── vars.yml
│   │   └── vault.yml          # ansible-vault encrypted
│   └── roles/
│       ├── proxmox_base/
│       ├── haos_vm/
│       ├── media_lxc/
│       └── unifi_lxc/
└── media-stack/
    ├── docker-compose.yaml    # Linux paths; image tags via .env
    └── .env.example
```

---

## Phase 0 — manual bootstrap (one time)

Everything after this is `ansible-playbook site.yml` from the laptop.

1. **Install Proxmox VE** on the Vaio from a USB stick. Give it a **static IP** on the LAN (`.10`).
2. From the laptop: `ssh-copy-id root@<pve-ip>` so Ansible can log in without a password.
3. **Install Ansible on the laptop**: `pipx install ansible` (or `brew install ansible`).
4. **Clone this repo**, set the Ansible Vault passphrase, and fill in `ansible/group_vars/all/vars.yml`
   (IP, external drive UUID, image tags, paths) and the encrypted `vault.yml` (passwords, tokens).

Automating the Proxmox install itself (answer file) is a possible later step, not v1.

---

## How to run

> Not wired up yet — the roles are being built. Target workflow:

```bash
cd ansible
ansible-galaxy collection install -r requirements.yml
ansible-playbook site.yml --ask-vault-pass
```

Re-running is safe (idempotent). "Does reality match the repo?" is answered by
re-running the playbook — there is no separate state file (see ADR-0003).

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
router despite the static public IP (see ADR-0006).

---

## Roadmap

**v1 (current):** media stack + Home Assistant + UniFi controller, flat network, Tailscale, backups.

**Later phases:**
- Smart-home: integrate the wired **BTicino MyHOME** bus via an OpenWebNet IP
  gateway (F454 / MyHOMEServer1) and the HACS OpenWebNet integration in HAOS.
  *Pending: confirm with the electrician whether an IP gateway is installed.*
- **Personal cloud** for documents + photos, with real redundancy.
- **Network segmentation** — IoT/camera VLAN. Needs a real L3 gateway (UniFi
  gateway or dedicated OPNsense box — **not** the Vaio). See `docs/network-topology.md`.
- **Frigate** — only on a future, more capable box (or with a Coral).
- Automated Proxmox install via answer file.

---

## Background

- Project glossary: [`CONTEXT.md`](./CONTEXT.md)
- Why things are the way they are: [`docs/adr/`](./docs/adr/)
