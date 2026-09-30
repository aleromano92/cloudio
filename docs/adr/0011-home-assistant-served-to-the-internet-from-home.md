# 0011 — Home Assistant served to the internet straight from home

Extends ADR-0010 to Home Assistant. The family's phones need the Companion app
to work away from home, and asking every family member to install and keep
Tailscale running was rejected, as it was for Jellyfin's viewers.

**Decision.** Caddy in the `media` LXC, already behind the forwarded TCP 443,
also serves `home.aleromano.com` and proxies it to the HAOS VM
(`192.168.7.11:80`). The `ddns` role keeps `home` pointing at the home IP along
with `jellyfin`. No new port is forwarded. HTTPS terminates at home, as for
Jellyfin: Vercel learns the IP and nothing else. Nabu Casa's remote access was
rejected on the same grounds as a Hetzner relay: a third party in the path of
the house's controls.

**Home Assistant's side** (runtime state, set in place, not by Ansible). Since
2026.9, HA keeps its HTTP settings in `.storage/http`, not `configuration.yaml`,
which it ignores for `http:` once migrated. There, `use_x_forwarded_for` is on,
`trusted_proxies` is `192.168.7.12` only, and `ip_ban_enabled` bans an address
after 5 failed logins (`login_attempts_threshold`). Tested 2026-09-30: a
forwarded-for header from any other LAN host gets a 400, and from the `media`
LXC a 200.

**Costs accepted.**
- The house's lights, shutters and everything added later answer to anyone who
  gets a login right. Every account uses a strong password and two-factor
  authentication (TOTP, set per user in their profile). Family members get
  their own non-administrator accounts.
- A ban is permanent until the address is removed from `ip_bans.yaml` in HA's
  config folder. A family member mistyping five times on mobile data bans
  their carrier's address, possibly shared with others.
- No NAT hairpin on the ZTE (ADR-0010), so at home the app must use the LAN
  address. The Companion app switches by Wi-Fi name: internal URL
  `http://192.168.7.11`, external URL `https://home.aleromano.com`.
- Proxmox, UniFi, the *arr apps and qBittorrent stay Tailscale-only (ADR-0006).
