# 0006 — Tailscale for remote access; nothing port-forwarded

> **Superseded for Jellyfin by [ADR-0010](0010-jellyfin-served-to-the-internet-from-home.md)**
> (2026-09-26): TCP 443 and TCP+UDP 6881 are now forwarded to the `media` LXC.
> Home Assistant followed on 2026-09-30 through the same port
> ([ADR-0011](0011-home-assistant-served-to-the-internet-from-home.md)).
> Everything else below still holds for every other service.

The 5G SIM has a publicly-routable IP with no CGNAT, so public port-forwarding is
technically possible. We deliberately forward nothing and reach the node only over
a Tailscale tailnet. Rationale: every forwarded port is exposed to the whole
internet, and a WireGuard mesh gives the same access with zero attack surface.

The public IP is also **dynamic** (observed rotating every few days). This does
not change the decision — it reinforces it. Tailscale is designed for exactly
this (mobile networks, CGNAT, rotating IPs): the node keeps a stable tailnet
address and MagicDNS name regardless, and no dynamic DNS is needed. A
port-forwarding design, by contrast, would have needed a DDNS client.

A public entry point is reconsidered only if a real need appears (e.g. Jellyfin
for family who won't install a VPN client) — and the first option then is
Tailscale Funnel (stable `*.ts.net` URL, still no port-forward, still no DDNS),
not a forwarded port.
