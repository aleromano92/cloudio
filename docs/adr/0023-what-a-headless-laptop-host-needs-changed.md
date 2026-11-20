# 0023 — What the Proxmox host needs changed to run headless

Applies to: `proxmox_base`'s `lid_switch.yml`, `apt_repos.yml`, `dns.yml`,
`tailscale.yml` and `blacklist_dgpu.yml`, and `dns_nameservers`. ADR-0001
records the laptop itself.

Each of these was found live on the box, not assumed.

- **The lid switch is ignored.** systemd-logind suspends on lid-close by
  default. That silently takes the whole server offline (network dead,
  Tailscale unreachable) without it actually being "off". It was found the
  hard way: after a power-cycle the router came back and `pve` didn't, and
  opening and closing the lid was the fix.
- **The enterprise apt repos are disabled.** Proxmox enables `pve-enterprise`
  and, since PVE 9, an enterprise Ceph repo too. Both return 401 without a paid
  subscription. PVE 9 writes them in deb822 format (`*.sources`), while older
  installs may still have one-line `*.list` files. Whichever exist are renamed,
  since apt ignores any other suffix, and `pve-no-subscription` is added. The
  apt cache is updated once, with retries, by `packages.yml`.
- **`/etc/resolv.conf` is managed.** `pve_ip` is static, not DHCP, and
  `resolvconf` isn't installed, so nothing else ever rewrites that file. The
  installer writes it once and never again. A router swap once left it pointing
  at an unreachable nameserver, which broke apt (and everything else) with DNS
  timeouts while the LAN itself was fine. The host and every LXC resolve
  through the router (`dns_nameservers`, derived from `pve_gateway`), not public
  resolvers. A router swap happens with physical access anyway, so a second
  hard-coded IP would only drift.
- **IP forwarding for Tailscale is set in `/etc/sysctl.d/99-tailscale.conf`.**
  Debian 13's systemd-sysctl only reads the `sysctl.d` directories at boot. A
  setting in `/etc/sysctl.conf` applied live and then vanished at the next
  reboot, silently cutting Tailscale off from everything behind `pve`. The old
  lines are removed from `sysctl.conf`.
- **The advertised subnet route is kept in sync with `tailscale set`.**
  `tailscale up` sets `--advertise-routes`, but it only runs at first auth,
  while the backend isn't "Running". Tailscale stays Running across a change of
  `lan_cidr`, because it rides the WAN, so the route would stay stale forever
  with no error anywhere. `tailscale set` updates it without the auth key.
- **The discrete GPU is blacklisted.** The GeForce GT 740M is unused on a
  headless server. Blacklisting its drivers means less power, less heat and
  fewer boot and suspend glitches.
