# 0010 — Jellyfin served to the internet straight from home

Supersedes ADR-0006 **for Jellyfin only**. Friends who won't install a VPN client
need to watch, which is exactly the "real need" ADR-0006 anticipated. Everything
else (admin UIs, the *arr apps, Proxmox, Home Assistant) stays Tailscale-only.

**Decision.** The ZTE forwards **TCP 443** to the `media` LXC, where Caddy
terminates HTTPS for `jellyfin.aleromano.com` and proxies to Jellyfin. The
certificate and its key are issued to and stored in the container, at home.
Because the 5G operator changes the public IP several times a day (eight
different addresses in one month, not "every few days" as ADR-0006 recorded),
the `ddns` role checks the IP every minute and updates the A record through the
Vercel DNS API with a 60 s TTL. **TCP+UDP 6881** is also forwarded, for
qBittorrent to seed (private trackers expect a connectable client).

**Why not through a cloud relay.** Two relay designs were considered and
rejected on privacy grounds: the owner won't have private films, music and
photos carried by any cloud provider. Proxying through the Hetzner server that
already hosts `aleromano.com` would have put TLS termination (and so readable
content) there. Tailscale Funnel, which ADR-0006 named as the first option,
also carries every stream through a third party's relays, and is not built for
sustained video bandwidth. With the direct design, the only thing a third party
learns is the IP: Vercel holds one DNS record, and the operator and everything
in between see ciphertext.

**What made it possible.** Tested 2026-09-26: the router's WAN IP is the public
IP (no CGNAT), and a listener in the LXC logged connections from outside
addresses on both forwarded ports, so the operator doesn't filter inbound.
Let's Encrypt validates over **443 alone** (TLS-ALPN-01), so port 80 stays
closed. An IP change was followed by the DNS record within the minute, with no
outage, on the first afternoon.

**Costs accepted.**
- 443 is open to the whole internet. Jellyfin itself is the attack surface:
  strong admin password, one account per friend, remote access granted per user.
- Anyone resolving the name learns the home IP.
- A modem re-attach breaks every open connection, streams included; players
  reconnect within a minute or two once the record has moved.
- The ZTE does no NAT hairpinning, so the public name doesn't connect from
  inside the house. At home, use `http://192.168.7.12:8096`. Split DNS was
  rejected: a DNS server on `pve` would make the whole house's DNS depend on it.
- Remote viewers share the 5G upload (~45 Mbps on a weak 5G cell, ~130 on a
  good one), so an internet streaming bitrate limit is set in Jellyfin.

**Fallback if inbound is ever blocked:** encrypted TCP passthrough via Hetzner
(the server forwards bytes it cannot decrypt; keys stay at home), not TLS
termination there.
