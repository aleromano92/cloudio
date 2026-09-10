# Runbook — Move the server to the new house

The node is being built in a temporary house (router / gateway `192.168.0.47`)
and later moves to the new house (router / gateway `192.168.0.1`). Same
`192.168.0.0/24` subnet, so only the gateway and a few baked-in values change.

**Safety net:** Tailscale does not use the local gateway. If the host's network
config is wrong after the move, SSH in over the tailnet (`ssh root@pve`, the
`100.x` address) and fix it from there.

## Before moving

1. Confirm the new router's LAN gateway is `192.168.0.1` and its subnet is
   `192.168.0.0/24`.
2. Confirm `192.168.0.10` is free on the new LAN and **outside** the new router's
   DHCP pool (shrink the pool if needed, e.g. start it at `.50`).
3. Note the MACs that need DHCP reservations on the new router: the HAOS VM, the
   MyHOME gateway, the Reolink NVR.

## On moving day

1. Physically move the Vaio; cable it to the new switch.
2. Power on. Get to the host — a monitor/keyboard, or `ssh root@pve` over Tailscale.
3. **Host gateway** — edit `/etc/network/interfaces`, in the `vmbr0` stanza change
   `gateway 192.168.0.47` → `gateway 192.168.0.1`. Then:
   ```
   systemctl reboot
   ```
   (Reboot rather than `ifreload -a` when changing the gateway — cleaner.)
4. **Container gateways** — for each LXC:
   ```
   pct set 112 -net0 name=eth0,bridge=vmbr0,ip=192.168.0.12/24,gw=192.168.0.1
   pct set 113 -net0 name=eth0,bridge=vmbr0,ip=192.168.0.13/24,gw=192.168.0.1
   pct reboot 112 && pct reboot 113
   ```
5. **HAOS VM** — it's on DHCP, so it just gets a new lease. Re-create its DHCP
   reservation on the new router (find its MAC in the Proxmox UI → VM 110 →
   Hardware → Network Device).
6. **Update the repo:** set `pve_gateway: "192.168.0.1"` in
   `ansible/group_vars/all/vars.yml`, commit.
7. **Reconcile the rest:**
   ```
   cd ansible
   ansible-playbook site.yml --ask-vault-pass
   ```

## Verify

- `ping -c1 192.168.0.1` from the host and from inside each container
  (`pct exec 112 -- ping -c1 192.168.0.1`).
- `tailscale status` on the host — still `Running`, still advertising the subnet.
- Web UIs reachable: Proxmox `:8006`, HA `:8123`, UniFi `:8443`.
- Re-run the external cellular test on the new WAN IP (guard against a stray
  port-forward on the new router) — see `network-topology.md`.
- Set DHCP reservations on the new router for the HAOS VM, MyHOME gateway, NVR.

## If `pve_ip` also has to change

Only if `192.168.0.10` is taken on the new LAN. Then also: change `pve_ip` and the
LXC IPs in `vars.yml`, update `/etc/network/interfaces` on the host, update
`inventory.yml` implicitly (it reads `pve_ip`), re-copy the SSH known_hosts entry,
and re-point any DNS/hosts entries. Easier to just free up `.10` on the new LAN.
