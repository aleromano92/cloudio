# 0021 — UniFi runs in Docker, with its inform IP pinned

Applies to: the `unifi_lxc` role and `unifi-stack/`. ADR-0009 records why it's
the UniFi Network Application and not UniFi OS Server.

**Decision.** The UniFi Network Application runs in its own unprivileged LXC,
separate from the media stack, so its 24/7 Java and MongoDB footprint stays
isolated. It runs as linuxserver.io's image plus a dedicated MongoDB 7
container.

**Why not a native install.** A native apt install (MongoDB 7, openjdk-17 and
Ubiquiti's own apt repo) was tried first and failed. Ubiquiti's `ubiquiti` apt
component was publishing an empty `Packages` file: the repo's signed
`InRelease` listed its MD5Sum as the hash of a zero-byte file. That was their
repo, not a config bug here. Docker sidesteps the repo entirely.
`init-mongo.sh` is linuxserver.io's documented script, unchanged. It runs once,
on an empty data dir, and creates the `unifi` database user with the root
account.

**`system_ip` is pinned to the LXC's address.** Left unset, the app
auto-detects its own address for provisioning. Inside Docker that is often the
container's bridge IP (such as `172.18.0.2`), which an AP can never reach.
Devices then check in fine through the published port, but adoption hangs
forever at `adopted: true` / `adoption_completed: false`. This was found by
testing against the real box, not assumed. The sign in `docker logs
unifi-network-application` is "Device adoption - process not finished. Reason:
timeout". Repeated "ucore/manifest ... Connection refused" lines next to it are
a harmless red herring.

Published ports: 8443 (admin UI), 3478/udp (STUN), 10001/udp (AP discovery),
8080 (device inform).
