# 0017 — Local backups live on a USB drive that can disappear

Applies to: `proxmox_base`'s `backup.yml`, `archive_mount.yml`,
`usb_media_mount.yml`, the `cloudio-backup*`, `cloudio-nightly-backup` and
`media-disk-reattach` templates, the udev rules, and the `backup_*`, `restic_*`,
`archive_*` and `media_disk_*` variables. The README's "External drives" covers
what each drive holds and how to restore.

**Decision.** The nightly `vzdump` of every guest goes to a Proxmox `dir`
storage on the archive drive. That is the old 2 TB NAS disk (WD20EARX), which
also holds the family's photos until a NAS exists. Only its large ext4
partition is mounted. The guests' root filesystems carry their apps' config and
state, so a whole-guest dump is the backup (ADR-0002). The first run on
2026-10-04 wrote about 15 GB (HA 4.2, media 8.2, unifi 1.9, stagista 0.9 GB),
so `backup_prune` needs roughly 200 GB. The off-site `restic` push switches on
by itself once `restic_storagebox_user` is no longer the placeholder, and needs
`vault_restic_password`.

**The system SSD must never take the dumps.** A missing drive leaves a bare
mount point on the SSD. Three guards:
- The storage has `is_mountpoint` set.
- The playbook checks with `findmnt` that the drive's *UUID* is mounted there,
  so another disk mounted in its place doesn't pass.
- The backup service has `RequiresMountsFor`, so systemd skips the run.

The backup directory is `0711`, not `0700`. `vzdump` of an unprivileged LXC
runs tar as the container's mapped root (uid 100000), which must be able to
pass through to its temp dir under `dump/`. It still can't list or read
anything.

**The report reads Proxmox, not the backup script.** The storage's content
list and the `vzdump` task log survive a reboot, and they include backups
started by hand from the web UI.
- While the drive is missing, the report uses the content list as last seen.
  A guest's newest dump therefore keeps ageing and turns stale.
- A night when the timer fired but no `vzdump` started shows as "not
  started".
- Stale means the newest dump is older than 26 h: 24 h, plus the timer's random
  delay, plus a run.
- The drive's readings expire after three missed hourly reports. The guests'
  readings don't expire, because their dump times already say how old they
  are. With no content list at all, the guests' last published state stays
  retained on the broker.
- A guest that's gone keeps its id as its name.
- The report runs hourly, so a drive that drops off shows within the hour. It
  also runs as `ExecStopPost`, so a failed run reaches Home Assistant the same
  night.
- It publishes over the signal monitor's MQTT library and login (ADR-0012), so
  it is a no-op, not an error, until that role has run.

**USB drives come back by themselves.** Both drives mount by UUID with `nofail`
and a 30 s device timeout, so a missing drive never blocks boot. USB
autosuspend is off, to keep the drives awake. When a drive drops off USB and
comes back (a power cut did this on 2026-10-02), nothing remounts it. The
`media` LXC keeps its bind mount of the dead filesystem, and every read fails
with "Input/output error". So a udev rule acts when the filesystem reappears:
- **The archive drive** gets its fstab mount unit started.
- **The media drive** gets `media-disk-reattach`. It replays the journal with
  `fsck -p`, then mounts the drive. Exit 0 means clean and 1 means errors
  fixed; anything else needs a human, so the drive is left unmounted. Then it
  reboots the `media` LXC if `/data` there can't be read. The unit runs after
  `local-fs.target`, so at boot it finds the drive already mounted and does
  nothing.
