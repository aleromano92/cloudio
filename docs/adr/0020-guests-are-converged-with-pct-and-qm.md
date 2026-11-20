# 0020 — Guests are converged with `pct` and `qm`, not only created

Applies to: the `docker_lxc`, `media_lxc`, `unifi_lxc`, `stagista_lxc` and
`haos_vm` roles, and the `lxc_template_*` and per-guest sizing variables.
ADR-0003 records why Ansible drives the native CLIs.

**One role per kind of guest.** `docker_lxc` builds one unprivileged LXC
running a compose stack. `media_lxc` and `unifi_lxc` import it and keep only
their own steps. `stagista_lxc` imports it with `docker_lxc_with_docker:
false`, which skips the AppArmor exception (ADR-0008), the Docker install and
the stack. The HAOS VM is built with `qm` directly, because importing a qcow2
image has no Ansible module equivalent.

**`pct create` sets some things only once, so later runs converge them.**
- **Network:** `net0` is rewritten when its IP or gateway differ from
  `vars.yml`. Without this an existing container would keep its old address
  forever. Its `hwaddr` is carried forward: omitting it makes `pct set --net0`
  generate a new random MAC, orphaning any MAC-to-IP binding on the router.
- **Disk:** the root disk is grown to the configured size. `pct resize` grows a
  running container in place but can never shrink one, so it only grows.
- **Reboots:** only a running container is rebooted to apply an AppArmor or
  network change. A stopped one picks it up when it starts, and `pct reboot`
  refuses a stopped container.

**CLI traps it works around.**
- `pveam download` can exit 0 without placing a usable template (for example
  when the storage's `content` lacks `vztmpl`). The size of the template file is
  therefore checked, so the failure doesn't surface much later, and more
  confusingly, in `pct create`.
- `pct push` runs on the node, so its source must be a node path. A
  control-node path fails silently: it prints an error and exits 0. Stack files
  are copied to the node first.
- A task that prints `CHANGED` or `UNCHANGED` is compared for equality, never
  by substring. `CHANGED` is a substring of `UNCHANGED`, and a substring test
  once made every run reboot a container.
- Files written inside the stagista container go through base64, so their
  content survives every layer of quoting. They are rewritten only when they
  differ.

**Base images.** LXCs default to Debian 12, deliberately not 13: trixie dropped
openjdk-17, which UniFi needs, and MongoDB's apt repo lags new Debian
codenames. stagista is on Debian 13: it needs neither, and 13's Python runs
current Ansible, matching a laptop's. The point release is bumped from
`pveam available --section system`.

**Sizing, and what set it.**
- `media` disk, 32 GB: Docker images, Jellyfin metadata and transcode temp files.
- `unifi` disk, 16 GB: Docker images plus Mongo's WiredTiger data.
- `stagista` memory, 4096 MB: 2048 OOM-killed Remote Control with about nine
  sessions, on 2026-10-07.
- `stagista` disk, 40 GB: 16 filled up building two Docker images at once, on
  2026-10-29.
