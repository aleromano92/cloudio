# 0008 — AppArmor unconfined for the Docker-hosting LXCs

The `media` and `unifi` LXCs run Docker inside an **unprivileged** container.
`features: nesting=1,keyctl=1` alone was not enough on this Proxmox VE 9 host:
Docker's `overlay2` storage driver failed to mount its image layers with
`permission denied` — a known interaction between current `lxc-pve`/containerd
and AppArmor's path-based confinement inside unprivileged containers. Verified
directly against the running `unifi` LXC before deciding, not assumed.

Fix, applied by `media_lxc`/`unifi_lxc`: add `lxc.apparmor.profile: unconfined`
to the container's config and `fuse=1` to its features. This is the standard,
widely-documented trade-off for Docker-in-LXC on Proxmox — it removes AppArmor's
Mandatory Access Control for that one container in exchange for working Docker.
Accepted because: the container is still **unprivileged** (the bigger boundary —
root inside the LXC still isn't root on the host) and still isolated from the
rest of the node by being its own LXC; this only affects `media` and `unifi`,
not `pve` itself or the `homeassistant` VM.
