# 0005 — Home Assistant runs as a VM, not an LXC

Despite a general preference for LXC on this node, Home Assistant runs as HAOS in a
full VM. This buys the Supervisor, one-click add-ons (Zigbee2MQTT, ESPHome, Matter,
Mosquitto) and first-class snapshots/backups — the assumed baseline for real
smart-home use. Cost: ~2 GB RAM reserved on a RAM-limited box. Learning when a VM
is the right tool is treated as part of the exercise, not a compromise.
