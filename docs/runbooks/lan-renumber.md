# Runbook — Renumber the LAN

Changes the base network (e.g. `192.168.0.0/24` → `192.168.7.0/24`) without
moving any hardware. Different from `house-move.md`, which is about physically
relocating the Vaio; this is the same location, just a new prefix — usually to
get off a subnet that collides with another network reachable over Tailscale
(the near-universal `192.168.0.x`/`192.168.1.x` consumer-router defaults are
the classic case).

**Do this with physical access to the Vaio.** `pve`'s own static network isn't
Ansible-managed (set once at Phase 0 install), and the moment it's wrong,
remote SSH/Tailscale access to fix it is gone too — you need a fallback that
doesn't depend on the network you're changing. A hard power-off if the console
ever becomes unresponsive is fine and recoverable; Debian/ext4 handles an
unclean shutdown well, and a fresh boot re-reads `/etc/network/interfaces`
from scratch anyway.

Keep every host's **last octet unchanged** — only the prefix moves. That
turns this into one find-and-replace instead of a full renumbering, and keeps
`docs/network-topology.md`'s addressing table valid without edits beyond the
prefix note at the top.

## Steps

1. **Repo first** (safe, nothing live changes yet) — in
   `ansible/group_vars/all/vars.yml`, update `pve_ip`, `pve_gateway`,
   `lan_cidr`, `media_lxc_ip`, `unifi_lxc_ip`, `zte_router_ip`. Commit + push.
   `inventory.yml` needs no change (it already reads `{{ pve_ip }}`); neither
   does `dns_nameservers` (it derives from `pve_gateway`).

2. **`pve`'s own network config** — edit `/etc/network/interfaces` (the
   `vmbr0` stanza's `address`/`gateway`). **Don't apply yet.**

3. **The router** — change its LAN IP and DHCP pool, and update every
   MAC-IP binding to the new prefix (same MACs, new IPs). Restart the router
   — most routers require this for bindings to actually take.

4. **Apply `pve`'s new config**, at the physical console:
   ```
   systemctl restart networking
   ```
   or `systemctl reboot` if that doesn't cleanly apply — a full reboot is the
   more reliable option and is what `house-move.md` recommends too. Verify
   locally before doing anything else:
   ```
   ip addr show vmbr0
   ping -c2 <new-gateway>
   ```

5. **Trust the new IP's SSH host key** from the control machine (same host,
   new address — SSH will refuse to auto-trust it otherwise):
   ```
   ssh -o StrictHostKeyChecking=accept-new root@<new-pve-ip> exit
   ```

6. **Re-run Ansible.** If the media drive isn't fitted yet, exclude it
   explicitly (running bare `site.yml` runs everything, including a role
   that isn't ready and will fail partway through, before later roles run):
   ```
   cd ansible
   ansible-playbook site.yml --ask-vault-pass --tags base,haos,unifi,monitoring
   ```
   `unifi_lxc`/`media_lxc` reconfigure an *existing* container's network on
   every run (not just at creation) and carry its MAC forward — this used to
   be a silent gap (existing containers kept their old IP forever) until it
   bit during the first real renumber; it's a normal, idempotent part of the
   role now. Same for the Tailscale advertised route — `proxmox_base`
   updates it on every run via `tailscale set`, not just at first auth.

## Verify

- `pct exec <ctid> -- ip addr show eth0` for each LXC — new IP, and check
  `grep net0 /etc/pve/lxc/<ctid>.conf` still shows the *original* `hwaddr`
  (a `pct set --net0` without an explicit `hwaddr=` silently generates a new
  random MAC, which orphans any router-side MAC-IP binding for it).
- Dashboard, Proxmox UI, UniFi UI all reachable at their new addresses.
- `tailscale debug prefs | grep -A2 AdvertiseRoutes` on `pve` shows the new
  subnet.

## Tailscale admin console (manual, outside Ansible's reach)

- **Approve** the newly-advertised subnet route.
- **Remove** the old subnet's route once the new one's confirmed working, or
  it lingers as a stale, never-matching entry.

## UniFi portal

If UniFi's own network is in "Third-party Gateway" mode (the ZTE/ISP router
is the real DHCP server, UniFi is just downstream), there's nothing to
change there — it doesn't cache its own subnet definition. Just confirm the
APs show their new addresses and **Online** in the device list; DHCP-reserved
devices (APs, HAOS) pick up the new prefix automatically once the router's
pool moves.

## Loose ends only a human can fix

Browser bookmarks/shortcuts pointing at the old IPs; any app that caches a
local LAN address for discovery (re-opening it is usually enough).
