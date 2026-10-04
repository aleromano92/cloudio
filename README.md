# Cloudio — Home Server

A single-node home server built on a repurposed Sony Vaio laptop running **Proxmox VE**.

This repo is the reproducible recipe: from a fresh Proxmox install, cloning it and
running one Ansible playbook rebuilds every service. It is also a deliberate
learning project — Proxmox, LXC, Ansible, and home networking.

> Status: **running on the real hardware** since September 2026: Proxmox, the
> media stack (served to the internet for Jellyfin only), UniFi, and the 5G
> monitoring. The smart-home gateway is blocked (see the roadmap), and
> **backups are not enabled yet** (`backups_enabled: false`).

---

## Hardware

| Part | Spec | Notes |
|---|---|---|
| Machine | Sony Vaio SVF153A1YM | Repurposed 2013 laptop |
| CPU | Intel Core i7-4500U (Haswell, 2c/4t) | H.264 hardware transcode via Quick Sync; **no HEVC hardware decode** |
| RAM | **16 GB** DDR3L-1600 SO-DIMM (2×8 GB) | Upgraded from 8 GB; 16 GB is the ceiling |
| GPU | Intel HD 4400 + GeForce GT 740M | dGPU is blacklisted (unused, saves power/heat) |
| System disk | 256 GB SSD | Proxmox + configs + container rootfs |
| Media disk | WD My Book 16 TB (WD160EDGZ, 7200 rpm), USB 3, ext4 | Media library only — **not backed up** (disposable). The enclosure encrypts in hardware with its own key: harmless, but the bare disk is unreadable outside it |

Frigate / local NVR is **out of scope** on this hardware. Camera recording stays on
the Reolink NVR's own disk.

---

## Architecture

One Proxmox node (`pve`) hosting:

| Guest | Type | Purpose |
|---|---|---|
| `homeassistant` | VM (HAOS, 2 GB / 2 vCPU) | Home Assistant OS with Supervisor + add-ons |
| `media` | LXC (Docker) | Jellyfin, Sonarr, Radarr, Lidarr, Prowlarr, qBittorrent, and Caddy (HTTPS for Jellyfin from the internet) via `docker-compose` |
| `unifi` | LXC (Docker) | UniFi Network Application + a dedicated MongoDB (controller for the U7 Pro Wall APs) |

Room is reserved for a 4th guest later: the personal-cloud phase (documents + photos, with real redundancy).

### Addressing

Static IPs on the infrastructure; DHCP reservations for everything else.

| Host | IP | Web UI |
|---|---|---|
| `pve` | `192.168.7.10` | Proxmox `https://192.168.7.10:8006`, signal dashboard `http://192.168.7.10:8420` |
| `homeassistant` | `192.168.7.11` | `http://192.168.7.11` — **port 80**, not HA's default 8123; `https://home.aleromano.com` from the internet |
| `media` | `192.168.7.12` | see [Media stack](#media-stack) |
| `unifi` | `192.168.7.13` | `https://192.168.7.13:8443` |
| `stagista` | `192.168.7.14` | none: `ssh aromano@192.168.7.14`, or Remote Control from claude.ai/code and the Claude app |

The same addresses work away from home with Tailscale on: `pve` advertises
`192.168.7.0/24` as a subnet route. That needs IP forwarding on `pve`, set in
`/etc/sysctl.d/99-tailscale.conf`; Debian 13 ignores `/etc/sysctl.conf` at boot.
No dedicated DNS server in v1.

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
│   ├── site.yml                # runs the roles below
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
│       ├── unifi_lxc/          # pct create, install Docker, deploy UniFi + Mongo
│       ├── signal_monitor/     # 5G signal + speedtest sampling, band scheduling, uplink watchdog
│       └── ddns/               # keeps jellyfin. and home.aleromano.com pointing at the home IP (Vercel DNS)
├── media-stack/
│   ├── docker-compose.yaml     # Linux paths; PUID/PGID/TZ/paths via .env
│   ├── Caddyfile               # HTTPS for Jellyfin, certificate kept at home
│   └── .env.example
└── unifi-stack/
    ├── docker-compose.yaml     # unifi-network-application + a dedicated MongoDB
    ├── init-mongo.sh           # from linuxserver.io's docs; creates the Mongo user
    └── .env.example
```

---

## Phase 0 — manual bootstrap (one time)

Everything after this is `ansible-playbook site.yml` from the laptop.

1. **Install Proxmox VE** on the Vaio from a USB stick. Give it a **static IP** on the LAN (`.10`).
2. **Note the UUIDs of the two external drives** (`blkid`): the media drive and the
   archive drive, both ext4, go in `media_disk_uuid` and `archive_disk_uuid`. The
   playbook mounts them.
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
ansible-playbook site.yml --ask-vault-pass --tags monitoring
ansible-playbook site.yml --ask-vault-pass --check           # dry run
```

Re-running is safe (idempotent). Ansible drives the native `pct` / `qm` /
`docker compose` CLIs directly — there is no Terraform and no state file; "does
reality match the repo?" is answered by re-running the playbook (see ADR-0003).

### Power cuts

The laptop rides out a power cut on its own battery (88 minutes on
2026-10-04, battery at about half its design capacity); the Wildix switch does
not, so the guests lose the network at once. `cloudio-power-watch.service` on
the host watches the adapter: after `power_watch_grace_minutes` (10) on
battery, or once the battery is down to `power_watch_min_battery` (30%), it
shuts every guest down cleanly (`pvesh create /nodes/pve/stopall`). The host
stays up on purpose: a laptop that was powered off stays off when mains comes
back, while one whose battery ran flat boots by itself and starts the onboot
guests. If mains returns while the host is still up, the onboot guests start
again after 2 minutes of steady power. Its log: `journalctl -u
cloudio-power-watch`. Deploy changes with `--tags power`.

Home Assistant also has three phone alerts (State, not in git): *Power: grid
outage*, *Power: grid restored* and *Power: house circuits dead*, the last one
firing when the Powerwall sees no house load for 2 minutes or HA loses the
Powerwall for 3. They only reach the phone while HA still has a path to the
internet.

### External drives

Two USB drives, both mounted by UUID with `nofail` (a missing drive never
blocks boot) and remounted by a udev rule if they drop off USB and come back:

- **Media** (`media_disk_uuid`, 16 TB) at `/mnt/media`: the library and
  torrents. Disposable data, not backed up.
- **Archive** (`archive_disk_uuid`, the old 2 TB NAS disk) at `/mnt/archive`:
  the family's photos and personal files (precious; they live here until a NAS
  exists) and the local backups under `cloudio-backup/`.

```bash
ansible-playbook site.yml --ask-vault-pass --tags storage,backup
```

**Backups.** `cloudio-backup.timer` runs `vzdump` of every guest (HA VM 110,
media 112, unifi 113, stagista 114) at 02:30 into the Proxmox storage
`archive-backup`, which keeps 7 daily, 4 weekly and 3 monthly dumps (about
15 GB a night, ~200 GB in all). They show up under that storage in the web UI
with a Restore button. The storage has `is_mountpoint` set, so with the archive
drive missing the job fails instead of filling the system SSD. The off-site
`restic` push switches on by itself once `restic_storagebox_user` is set. Its
log: `journalctl -u cloudio-backup`.

### Media stack

Everything runs in the `media` LXC (`192.168.7.12`). On the LAN, or from
anywhere with Tailscale on (the node advertises `192.168.7.0/24` as a subnet
route):

| App | URL | Reachable from the internet |
|---|---|---|
| Jellyfin | `http://192.168.7.12:8096` | yes, as `https://jellyfin.aleromano.com` |
| qBittorrent | `http://192.168.7.12:8080` | no |
| Sonarr | `http://192.168.7.12:8989` | no |
| Radarr | `http://192.168.7.12:7878` | no |
| Lidarr | `http://192.168.7.12:8686` | no |
| Prowlarr | `http://192.168.7.12:9696` | no |

**The drive.** `/mnt/media` on the host is `/data` in the container:
`media/{movies,tv,music}` for the library and `torrents/` for qBittorrent
(`DefaultSavePath=/data/torrents`). They share one filesystem on purpose, so the
*arr apps hardlink a finished download into the library instead of copying it.
Copying the library anywhere must keep that: one `rsync -aH` of the whole tree
in a single run, since rsync can only see that two names are one file within
one invocation. Formatted with no reserved blocks (`-m 0`, which would
otherwise waste ~800 GB) and one inode per MB (`-T largefile`).

**If the drive drops off.** The laptop rides out a power cut on its battery;
the drive does not. When it comes back, a udev rule runs
`media-disk-reattach.service` on the host: it `fsck -p`s and remounts
`/mnt/media`, then reboots the `media` LXC if `/data` there is unreadable
(the LXC otherwise keeps the dead mount and Jellyfin fails with "Input/output
error"). Its log: `journalctl -u media-disk-reattach`. If fsck needs a human,
it leaves the drive unmounted and says so there.

**Ownership.** The container is unprivileged, so its user 1000 (the stack's
`PUID`) is user **101000** on the host, and the container's own root has no
rights over the drive at all. The role therefore creates the drive's folders
from the host, owned by 101000. Anything copied onto the drive from the host
needs `chown -R 101000:101000` afterwards.

**Jellyfin from the internet** (why and how: [ADR-0010](docs/adr/0010-jellyfin-served-to-the-internet-from-home.md)):
- The ZTE forwards TCP 443 to Caddy, which serves `jellyfin.aleromano.com` with
  a Let's Encrypt certificate obtained over 443 alone (port 80 stays closed).
  The certificate and its key live in `/opt/appdata/caddy` in the container.
- The `ddns` role checks the public IP every minute and updates the A record
  through the Vercel API (`vault_vercel_token`, a token scoped to the Vercel
  team that holds the domain). Every change is logged to
  `/var/log/cloudio-ddns/changes.jsonl` on `pve`. On each change it also runs
  `ddns_on_ip_change`, which makes qBittorrent re-announce every torrent, since
  qBittorrent can't see the public IP change from behind Docker and the router.
  Public torrents re-announce at once; private-tracker ones (ItaTorrents) wait
  for the tracker's minimum announce interval, which qBittorrent rightly obeys.
- **Set by hand, not by Ansible:** Jellyfin trusts Caddy as a proxy
  (`KnownProxies` = `127.0.0.1` in `/opt/appdata/jellyfin/config/network.xml`),
  so viewers count as remote rather than local. Also in Jellyfin's dashboard:
  one account per friend with remote access, and an internet streaming bitrate
  limit, since remote viewers share the 5G upload.
- **At home, use the LAN address.** The ZTE doesn't loop connections to its
  own public IP back inside, so `jellyfin.aleromano.com` doesn't connect from
  the LAN.
- Jellyfin runs on host networking, so LAN discovery (7359/udp) and DLNA
  (1900/udp) work and it sees clients' real addresses.

**Home Assistant from the internet** (why and how: [ADR-0011](docs/adr/0011-home-assistant-served-to-the-internet-from-home.md)):
the same Caddy also serves `home.aleromano.com` and proxies it to the HAOS VM,
for the family's Companion apps. Nothing else is forwarded for it.
- **Set by hand, not by Ansible:** HA trusts only `192.168.7.12` as its proxy
  and bans an address after 5 failed logins. Since 2026.9 these live in HA's
  `.storage/http`; an `http:` block in `configuration.yaml` is ignored.
  Unban by deleting the address from `ip_bans.yaml` and restarting HA.
- Every account has two-factor login on; family members are non-administrators.
- **In the Companion app**, set the internal URL `http://192.168.7.11` with the
  home Wi-Fi name, and the external URL `https://home.aleromano.com`: with no
  hairpin on the ZTE, the public name doesn't connect from the LAN.

**qBittorrent** listens on 6881, forwarded (TCP and UDP) by the ZTE so peers can
connect to it. Its settings are code: `qbittorrent_preferences` in `vars.yml`,
applied through its web API after every deploy by
`media-stack/qbittorrent-configure.py`, which changes only what differs (its
own config file is rewritten on every exit, so it can't be the source of
truth). On a fresh container it first allows API calls from inside the
container itself, so no WebUI password is involved. The policy:

| | Weekdays 08:00–19:00 | Nights and weekends |
|---|---|---|
| Upload | 1.5 MiB/s (~12 Mbps) | 5 MiB/s (~42 Mbps) |
| Download | 10 MiB/s | unlimited |

Every torrent seeds, forever: no queue, no ratio or seeding-time limit, 20
upload slots per torrent, up to 500 files open at once (a 107-file pack sits
among 30+ torrents). The WebUI's CSRF and clickjacking protections are on:
they were found off, which would let any page open in the same browser as a
logged-in WebUI send it commands. Radarr and Sonarr use the API without
browser headers, so they're unaffected (their connection tests pass). The weekday cap leaves room for two people on video
calls even on a weak 5G cell (~45 Mbps up). The night cap stays well short of
the upload so friends' Jellyfin streams keep working, and so the watchdog's
pings don't fail on a saturated link and trigger a false outage. The SIM is
unlimited, so volume isn't a constraint. Speeds in `vars.yml` are bytes/s,
which is the API's real unit whatever its docs say.

Torrents re-added after the Mac migration sit in the `reseed` category, which
no *arr app watches, so none of them tries to import them again.

**Migrated from the Mac** on 2026-09-26: the library (1,909 files, with every
hardlink kept) and every app's config and database from `~/cloudio-volumes`.
The library paths inside the containers didn't change, so nothing needed
rewriting.

### 5G/4G signal + speedtest monitoring

The `signal_monitor` role samples the ZTE MC801A's signal metrics plus a
speedtest on `signal_monitor_on_calendar` (default hourly at :57) to
`/var/log/cloudio-signal/metrics.jsonl` on `pve`, and writes a daily text
digest to `signal_log_dir/digests/`. Both toggles below start **off**:

- `zte_router_enabled: false` — the router locks logins out after 5 failed
  attempts. Set `vault_zte_router_password` to the real admin password first,
  then flip this to `true`.
- `signal_email_enabled: false` — the digest file is always written; email
  additionally needs an SMTP relay (`signal_email_smtp_*` vars +
  `vault_signal_email_smtp_password`, e.g. a Gmail app password).

A static page (`files/dashboard.html`, no build step, no external CDN) is
served straight off `pve` via `npx serve` on `signal_web_port` (default
`8420`) — open `http://<pve_ip>:8420` (or the Tailscale address) and reload
to refresh; it fetches `metrics.jsonl` client-side and draws it as plain SVG.

```bash
tail -f /var/log/cloudio-signal/metrics.jsonl              # on pve
cat /var/log/cloudio-signal/digests/$(date -u +%F).txt
```

### Band scheduling and the uplink watchdog

The home mast (`7b1e2`) switches its **B1 carrier off overnight** while B3 and
B20 on the same mast stay up. A lock on B1 alone therefore pushes the modem onto
a distant mast at around −124 dBm, where it passes next to nothing. First
measured 2026-09-19: unlocked at 00:31, the modem was back on `7b1e2` within
45 seconds, and a B20 lock carried ~300 Mbps all night against ~0 on the
nights before.

Three pieces, all needing `zte_router_enabled`:

- **`cloudio-band-day.timer`** (`band_day_on_calendar`, default 07:13) locks
  4G `band_day_lte` and 5G `band_day_nr`. `band_day_lte` is a list: several
  bands in one lock let the modem aggregate them.
- **`cloudio-band-night.timer`** (`band_night_on_calendar`, default 00:30,
  toggled by `band_night_enabled`) reboots the modem if it has no service at
  all, unlocks every band, logs the neighbour cells it can now see, measures each
  band in `band_night_candidates` in turn, and locks the best one that carries
  traffic. Any unexpected exit restores AUTO rather than stranding the link.
- **`cloudio-watchdog.service`** (`watchdog_*`) pings `watchdog_targets` from
  `pve` every 10s. "Down" means all of them failed 3 times running. It measures
  traffic, not the router's own report, because the router reports itself
  attached with a WAN IP while passing nothing. On an outage it climbs a ladder
  and stops at the first rung that brings traffic back: **4G AUTO** (the modem
  measures every band at once and picks) → **lock `watchdog_known_good_lte`** →
  **reboot the modem**, at most once per `watchdog_reboot_cooldown_minutes`.
  Whatever fixed it stays until the next scheduled band change, so recovering
  never costs a second interruption. Outages show on the dashboard as a strip
  above the charts.

**Result of the 2026-09-19 experiment (kept):** the day lock is B1+B3+B20 +
n78, and the night sweep stays paused as a fallback. With the three bands
allowed, the modem sits on **B3**, which is a better band here than B1, and
never needed B1 at all, so B1 switching off at midnight costs nothing. Its
three nights averaged 364–539 Mbps, against ~0 before. The modem never actually
aggregated the bands; the gain is B3. The 5G cell matters more than the 4G
band: two good n78 cells here (PCI `1e`, `1f`, ~−70 dBm, ~130 Mbps upload) and
one poor one (`15`, ~−100 dBm, ~48 Mbps upload). The network, not the modem,
picks it, so no lever on our side moves it.

Everything writes JSON lines next to `metrics.jsonl`:

```bash
jq -c 'select(.event == "up")' /var/log/cloudio-signal/watchdog-events.jsonl
jq -c 'select(.step == "probe") | {band, score, served}' \
  /var/log/cloudio-signal/band-events.jsonl
systemctl list-timers 'cloudio-*'; systemctl status cloudio-watchdog
```

A dry rehearsal of the watchdog that changes nothing on the router is
documented at the top of `templates/cloudio-watchdog.sh.j2`.

Every job that talks to the router shares one session library
(`files/zte-session.sh`, installed at `/usr/local/lib/cloudio/`), so there's a
single implementation of the login hash, the `AD` command signature and the
band-mask encoding. They also share one lock, `/run/lock/cloudio-zte.lock`. The
router keeps **one logged-in session at a time** and answers an evicted session
with empty strings rather than an auth error, so two jobs at once would quietly
spoil each other's readings. The same eviction happens when you open the
router's web UI in a browser, which is why the library's read and set helpers
re-login and retry.

### Hardware transcoding

Jellyfin hardware transcoding (Intel Quick Sync — **H.264 only** on this CPU, no
HEVC) needs the render node (`/dev/dri/renderD128`) exposed to the unprivileged
`media` LXC: add `lxc.cgroup2.devices.allow` + `lxc.mount.entry` lines to
`/etc/pve/lxc/112.conf`, then uncomment the `devices:` block in
`media-stack/docker-compose.yaml`. Left disabled in this draft — direct play and
software transcode work without it. TODO: fold this into the `media_lxc` role.

### stagista (Claude Code on the server)

An LXC (`stagista_lxc` role, Debian 13, no Docker) where Claude Code does the
coding work, so a session doesn't depend on a laptop staying awake. It holds
the repos under `~/code` (cloudio included) and its own SSH keys, generated
inside it and never copied: root on `pve` (authorised by the role), `axel` on
the Hetzner server, and a GitHub **account** key, since it works on every
personal repo. The vault password is never stored there; playbooks are still
run by a person typing it.

- **SSH in** and you land in the persistent tmux session `cloudio`, running
  Claude Code in `~/code/cloudio`. Disconnecting leaves it running; the next
  login reattaches. For a plain shell: `ssh -t aromano@192.168.7.14 NO_TMUX=1 bash -l`.
- **Other repos** in `~/code` each get their own session with `proj <folder>`:
  `ssh -t aromano@192.168.7.14 '~/.local/bin/proj aleromano.com'`, or run
  `proj <folder>` inside tmux to switch. `proj` alone lists sessions and folders.
- **From the phone or a browser**, the `claude-remote-control` service runs
  `claude remote-control` in `~/code`: open the Code tab in the Claude app, or
  claude.ai/code, and start a session there, running on stagista.
- **Once, by hand, before that service can run:** sign in to Claude, trust
  `~/code` (`cd ~/code && claude`), and accept the Remote Control prompt
  (`cd ~/code && claude remote-control`, then Ctrl+C). Claude never remembers
  trust for a home folder, hence `~/code`. The role enables the service once
  Claude is signed in and `~/code` trusted; until the Remote Control prompt
  is accepted, the service exits and retries every 30 s.

---

## What lives in git, and what does not

- **In git:** how to build the node — playbooks, roles, the compose file, hand-written base config.
- **Not in git:** runtime *state* — Home Assistant's config after UI edits, the *arr
  SQLite databases, qBittorrent data, UniFi's MongoDB. That is protected by
  **backups**, not version control (see ADR-0002).

**Backups:** nightly `vzdump` of every guest to the archive drive (running), plus a
nightly `restic` push to a Hetzner Storage Box (the only off-site copy; not set up
yet). Media is not backed up.

---

## Remote access

Tailscale on the node, the laptop, and phones, for everything administrative:
Proxmox, UniFi, the *arr apps and qBittorrent (ADR-0006).

**Two exceptions are port-forwarded on the ZTE**, both to the `media` LXC: TCP
443, where Caddy serves Jellyfin at `https://jellyfin.aleromano.com` so friends
can watch without a VPN client, and Home Assistant at
`https://home.aleromano.com` for the family's Companion apps; and TCP+UDP 6881
for qBittorrent to seed. The public IP changes several times a day, which the
`ddns` role follows (ADR-0010, ADR-0011).

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
