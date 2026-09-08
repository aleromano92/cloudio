# 0006 — Tailscale for remote access; nothing port-forwarded

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
