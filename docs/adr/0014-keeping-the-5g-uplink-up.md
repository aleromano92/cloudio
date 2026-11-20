# 0014 — Keeping the 5G uplink up: traffic decides, a ladder recovers

Applies to: `cloudio-watchdog.sh.j2`, `cloudio-band-night.sh.j2`,
`cloudio-band-day.sh.j2`, their units and timers, and the `watchdog_*` and
`band_*` variables. The README's "Band scheduling and the uplink watchdog"
covers how they behave and the 2026-09-19 experiment. This records why.

**"Down" is measured, not reported.** The Router reports itself attached, with
a WAN IP, while passing no traffic at all (seen on B1 at −127 dBm). So pings
from `pve` decide whether anything is wrong. The Router's own state is logged
next to each event, to say why. Down means *every* target failed, so one
unreachable resolver isn't an outage.

**The ladder.** On an outage the watchdog stops at the first rung that brings
traffic back:
1. **AUTO** unlocks the LTE bands. The modem measures every band at once and
   picks, which recovered in under 45 s where our own sequential sweep took six
   minutes. NR stays locked: it held every night on record.
2. **Known-good**: LTE locked to `watchdog_known_good_lte` (B20, the band
   proven good overnight). This is for when AUTO latches onto a distant mast.
3. **Reboot** the modem, at most once per `watchdog_reboot_cooldown_minutes`,
   so a genuine operator outage doesn't become a reboot loop.

Whatever fixed the link stays until the next scheduled band change. Returning
to the intended lock at once would be a second, deliberate interruption. A
ladder that ran out of rungs waits for the reboot cooldown before it climbs
again, rather than churning bands through an operator outage.

**A stalled link reboots the modem too.** On 2026-10-15 the link answered
pings and short exchanges for nine hours while every speedtest stalled, until a
reboot cleared it. Single failures do happen (three on 2026-10-13). So the
modem is rebooted only after `watchdog_speedtest_fail_threshold` failed hourly
speedtests in a row, all since the last reboot:
- Each new sample is checked once.
- A reboot that didn't help waits for as many fresh failures.
- This reboot and the ladder's share one last-reboot timestamp, so neither
  reboots straight after the other.
- The first ping comes 30 s after the reboot, because the modem takes a few
  seconds to drop the link. A ping before then would pass and call it
  recovered. If the link isn't back, the main loop sees an outage and climbs
  the ladder, and the cooldown skips its reboot rung.

**Staying observable.**
- The uplink state goes to Home Assistant at once on a change. Otherwise it is
  sent once a minute as the heartbeat HA's `expire_after` watches (ADR-0012).
  It also keeps going while a rung waits, so the heartbeat never lapses.
- Publishing runs in the background, so a broker that hangs never delays a
  ping.
- A dry-run rehearsal publishes nothing, because HA would show an outage that
  isn't happening.
- `Restart=always`: the watchdog is what recovers the link, so it must outlive
  its own bugs.
- It sources its libraries once at start, so a new script, library or unit
  takes effect only on a restart. The role's handler does that.

**The night sweep.** The home mast switches B1 off overnight. The sweep
reboots the modem first if it has no service. It then unlocks every band and
measures each candidate in turn (B1, B3, B7, B20, B28, in that order). B7 is
there for completeness: it is the least likely to reach a distant mast. B20
and B28 are the long-reach bands. It locks the best band that actually has
service, or leaves AUTO.
- Any unexpected exit restores AUTO. A band lock with nothing reachable would
  strand the connection until morning.
- The neighbour list is logged only once every band is allowed. Under a lock,
  the modem only reports its own frequency.
- **Score = RSRP + 2 × SNR.** A strong but noisy cell carries no more than a
  weak clean one. A `null` reading scores below any real measurement.
- **Service** means registered and carrying traffic: not `LIMITED_SERVICE`,
  and a WAN IP.
- After every band change the modem gets `band_settle_seconds`, then a retry
  loop. It answers every field blank while re-registering, and a blank reading
  would otherwise score as "this band has no coverage".
- `band_night_timeout_seconds` covers a reboot, plus one settle and its
  retries per candidate, plus slack.

**The day lock and pausing.** Several LTE bands in one day lock let the modem
aggregate them. The night timer is enabled or disabled from
`band_night_enabled` both ways. Pausing the sweep is therefore a `vars.yml`
change, not a manual `systemctl` that the next run would quietly undo.
