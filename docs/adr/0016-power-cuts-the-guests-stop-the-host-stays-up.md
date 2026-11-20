# 0016 — Power cuts: the guests stop, the host stays up

Applies to: `proxmox_base`'s `power_watch.yml`, `ups.yml`,
`cloudio-power-watch.sh.j2` and its unit, the NUT templates, and the
`power_watch_*` and `ups_*` variables. The README's "Power cuts" has the
numbers and the Home Assistant alerts.

**Decision.** `cloudio-power-watch` stops the guests cleanly and leaves the
host running.
- **On UPS battery** the guests keep running, so Home Assistant can still
  alert the phone. They stop once the UPS flags low battery or has
  `power_watch_ups_min_runtime_minutes` left. That is before the USB disks lose
  power with the UPS.
- **On the laptop's own battery** (the UPS ran out or can't be read), the
  Wildix switch is dark and the guests serve nobody. On 2026-10-04, before the
  UPS, mains went at 05:38 and the laptop crashed at 07:06. So the guests stop
  after a grace period, or at a battery floor, whichever comes first.

**Why the host stays up.** A laptop that was powered off stays off when mains
comes back. One whose battery ran flat boots by itself (it did on 2026-10-04)
and starts the onboot guests. If mains returns while the host is still up, the
watch starts the onboot guests itself once mains has been steady for
`power_watch_restore_minutes`.

**Rules that follow from it.**
- Mains counts as lost when the UPS is on battery or the laptop's adapter is
  offline.
- **No stop on a guess.** An unreadable UPS gives no signal, and then the
  adapter alone decides. `upsc` returns nothing when upsd is down, when the
  driver has lost the UPS, or when its data is stale. An unreadable adapter
  counts as mains.
- The "guests stopped" marker lives in `/run`, so a reboot clears it.
- The unit starts after `pve-guests`, which starts the onboot guests at boot:
  the watch only acts on later changes. It also starts after `nut-server`;
  without it, the watch goes by the adapter.
- **NUT** runs the `usbhid-ups` driver plus `upsd`, listening on localhost for
  the power watch and on `pve_ip` for Home Assistant.
  - `upsd.users` is empty, so nobody can send the UPS commands.
  - `upsmon` stays off, because it would power the host down.
  - NUT's udev rule only covers devices added after it was installed, so the
    playbook re-triggers it once for the UPS already plugged in.
