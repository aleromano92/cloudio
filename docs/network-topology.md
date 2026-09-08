# Network topology

## Physical

```
                 5G LTE router (outside)
                 public IP: DYNAMIC (changed 2.192.6.1 -> 2.192.6.72 over ~10 days),
                 non-CGNAT / publicly reachable, normal NAT to LAN
                          │  1 × ethernet
                          ▼
        ┌─────────────────────────────────────────────┐
        │      Wildix 24-port managed PoE switch       │  ← core switch, all rooms home-run here
        └─────────────────────────────────────────────┘
          │            │            │            │
          │            │            │            └── Reolink NVR (+ cameras)
          │            │            └── Vaio / Proxmox node (pve)
          │            │
     PoE+ inj. ×2  PoE+ inj. ×1
          │            │
   U7 Pro Wall    U7 Pro Wall
   (main floor)   (semi-basement)
```

- Office and every room: wired ethernet back to the Wildix switch.
- APs are powered by standalone PoE+ injectors (not the switch).
- The 5G router is the only L3 device. It does **normal NAT**; the LAN is private,
  nothing is exposed unless explicitly forwarded — and nothing is forwarded.
- The public IP is **dynamic** (rotates every few days) but that is irrelevant:
  remote access is Tailscale-only (ADR-0006), which does not use the public IP.
  No dynamic DNS is needed. Hygiene: confirm the router's inbound firewall is
  default-deny and remote admin is disabled.

## Logical — v1 (flat)

One subnet. No VLANs. See [ADR-0004](./adr/0004-flat-network-for-v1.md).

### Addressing

Infrastructure gets **static IPs configured on the device itself** (not DHCP
reservations) so it does not depend on the DHCP server being healthy. Everything
else (phones, TVs, IoT) gets a **DHCP reservation** so addresses are still stable
for the future VLAN split.

| Host | Last octet | Notes |
|---|---|---|
| `pve` (Proxmox node) | `.10` | Static, set at install |
| `homeassistant` (HAOS VM) | `.11` | Static |
| `media` (Docker LXC) | `.12` | Static |
| `unifi` (UniFi controller LXC) | `.13` | Static |
| BTicino OpenWebNet gateway | TBD | Installed gateway is an **F460** = Home+Control only, **no OpenWebNet**. Needs a separate OWN gateway (F454 / F459 / MH201) added alongside, or swap to F461. Smart-home phase. |
| Reolink NVR | TBD | DHCP reservation; block from internet if switch supports ACLs |

Name resolution: Tailscale MagicDNS for remote; a local hosts/DNS entry per
infra host for LAN. No dedicated DNS server in v1.

### Cheap isolation wins available without VLANs

- **Client isolation** on the IoT Wi-Fi SSID (IoT devices cannot talk to each other).
- **Block the Reolink NVR/cameras from the internet** via port ACLs on the Wildix
  switch, if supported.

## Logical — Phase 2 (segmented)

Deferred. Requires a real L3 device that can **route and firewall between VLANs**:
a UniFi gateway (e.g. a Cloud Gateway) or a dedicated OPNsense box.

**Not** the Vaio — a 2-core laptop must not be the single point of failure for all
household internet.

Planned VLANs (draft):

| VLAN | Purpose | Inter-VLAN policy |
|---|---|---|
| Trusted | Laptops, phones, the Proxmox node | Full access |
| IoT | Wi-Fi smart devices, BTicino gateway | HA (trusted) may reach IoT; IoT may not initiate to trusted; no internet for devices that don't need it |
| Cameras | Reolink NVR + cameras | No internet; reachable only from HA/NVR clients |
| Guest | Visitors | Internet only, fully isolated |

Open questions for Phase 2: mDNS reflection for HA discovery / casting across
VLANs; where the gateway sits relative to the Wildix switch and the 5G router.
