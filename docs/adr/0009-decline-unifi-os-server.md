# 0009 — Decline UniFi OS Server; stay on the classic Network Application

The UniFi web UI nags to upgrade from the classic self-hosted Network
Application (what `unifi_lxc` deploys) to **UniFi OS Server**. Declined for now
("Remind Me Later"). UniFi OS Server is a different shape of thing, not a
version bump: it runs on **Podman** (a second container runtime, not the Docker
this whole stack standardises on), wants a 20 GB minimum footprint, and is
designed as an OS-level platform hosting multiple UniFi apps — pulling toward
Ubiquiti's cloud ecosystem (Identity, Cloud Backups, Site Manager, **Teleport**).
Teleport duplicates Tailscale (ADR-0006); Cloud Backups duplicates restic →
Hetzner (ADR-0002/ADR-0004). Adopting it would mean either ignoring most of what
it adds, or drifting toward vendor-cloud dependency this build deliberately
avoids. The classic app keeps working regardless of the nag. Revisit if a real
need appears (multi-site SD-WAN doesn't apply here) or on a future, larger box.
