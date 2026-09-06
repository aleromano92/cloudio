# 0006 — Tailscale for remote access; nothing port-forwarded

The 5G SIM has a static public IP with no CGNAT, so public port-forwarding is
technically easy. We deliberately forward nothing and reach the node only over a
Tailscale tailnet. Rationale: every forwarded port is exposed to the whole
internet, and a WireGuard mesh gives the same access with zero attack surface. A
public reverse proxy is reconsidered only if a real need appears (e.g. Jellyfin for
family who won't install a VPN client).
