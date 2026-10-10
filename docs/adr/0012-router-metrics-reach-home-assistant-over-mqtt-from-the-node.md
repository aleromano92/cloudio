# 0012 — Router metrics reach Home Assistant over MQTT, published from the node

The Router's signal, the hourly speedtest and the watchdog's view of the uplink
were only on the static page at `:8420`. They matter to the house, so they
belong in Home Assistant, next to the Casetta's Shelly temperature and
humidity.

**Decision.** The node stays the Router's only client. The `signal_monitor`
role's sampler and watchdog publish what they already measure to the Mosquitto
add-on in HA, as one MQTT-discovered device, "Router 5G", in area Casetta
Legno. Home Assistant never logs in to the Router and never runs a speedtest of
its own.

**Why not an integration in HA.** HA could read the Router itself (a custom
integration, or `rest` sensors replaying the login). But the Router keeps one
logged-in session at a time and answers an evicted session with blank fields
rather than an error. A second client would spoil the watchdog's diagnosis, the
band jobs and the hourly sample, which already serialise on one lock on the
node. A speedtest in HA would also run at a different minute from the node's,
saturating the link while the watchdog's pings run.

**Why MQTT rather than a webhook or the REST states API.** Discovery creates a
real device with stable unique IDs, defined from the repo by the role (Config),
not by hand in HA's YAML (State). Retained messages mean HA has every value
again right after it restarts. States posted through `/api/states` have no
unique ID, can't go in an area, and vanish on a restart.

**Costs accepted.**
- A broker to keep: the Mosquitto add-on, installed and given the node's login
  by hand (HA's side is State, ADR-0002). The password lives in two places,
  the vault and the add-on's options, and they must match.
- Fire-and-forget. While HA or the broker is down, HA gets a gap. Nothing is
  queued or replayed; `metrics.jsonl` stays the complete record.
- HA's history starts on 2026-10-10. Earlier samples stay in `metrics.jsonl`
  only.
- Readings expire after 2 hours without a sample, and the uplink after 3
  minutes without the watchdog's heartbeat, so a stopped publisher shows as
  unavailable rather than as a stale value.
