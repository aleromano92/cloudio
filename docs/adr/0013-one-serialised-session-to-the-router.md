# 0013 — One serialised session to the Router

Applies to: the `signal_monitor` role, mainly `files/zte-session.sh`, the
`cloudio-signal-monitor`, `cloudio-band-*` and `cloudio-watchdog` scripts and
units, and `files/openssl-legacy.cnf`.

The sampler, the band jobs and the watchdog all drive the ZTE MC801A through
its `goform` web API. The Router keeps **one logged-in session at a time** and
answers an evicted session with blank fields rather than an auth error. Opening
its web UI in a browser evicts our session the same way.

**Decision.** Every job goes through one library, `zte-session.sh`, and holds
one lock, `/run/lock/cloudio-zte.lock`, for as long as it talks to the Router.
Two of our own jobs at once would otherwise quietly spoil each other's readings.
The library's functions take the Router's IP and a cookie jar as arguments, so
nothing in it depends on the caller's globals.

**Rules that follow from it.**
- A blank answer is ambiguous, so the read and set helpers log in again and
  retry. The sampler tells eviction apart from a real loss of signal with one
  re-login. A loss of signal is recorded as the `null` it is. A set command
  that fails without its `AD` token gets one re-login before giving up.
- The hourly sample *waits* for the lock (up to 900 s) rather than skipping,
  because the night probe holds it for minutes. Each unit's `TimeoutStartSec`
  covers its lock wait plus its own work: systemd's default 90 s start timeout
  is less than the wait alone.
- Failures while another job holds the lock aren't evidence. The hourly
  speedtest saturates the link, and the night sweep changes bands on purpose.
  So the watchdog doesn't count them.
- Readings come back as strings, with `""` for "not measured" and `-32768` (or
  `-3276.8`) for the modem's own "no value". Both become `null`, so they are
  never averaged or compared as if they were 0. This typing lives in the
  library, so `metrics.jsonl` and the band scheduler agree on what a missing
  reading looks like. A failed request gives `{}`: jq exits 0 and prints
  nothing on empty input, which would otherwise pass an empty string off as a
  reading.

**How the API was learnt.** The login hash, the `AD` token and the band masks
were read off the Router's own JavaScript and the Miononno bookmarklet, not
guessed:
- The password is hashed client-side, the way the Router's web UI does it:
  `SHA256(SHA256(password) + LD)`, upper-case hex, with `LD` fetched first. So
  the vault holds the plaintext admin password.
- Every set command is signed with
  `AD = md5(md5(wa_inner_version + cr_version) + RD)`. It is read fresh each
  time, because `RD` is a nonce.
- LTE bands are a bitmask: band N is bit N-1. `AUTO` is the firmware's own
  "every supported band" constant `0xA3E2AB0908DF`. A mask with more than 8
  bands is shown as AUTO. NR bands are a comma-separated list, not a mask.
- The neighbour list reports EARFCNs, not band numbers. They are mapped to
  bands only for the bands this operator uses here.
- The Router's TLS needs `UnsafeLegacyRenegotiation`, so every request runs
  with `OPENSSL_CONF` pointing at `openssl-legacy.cnf`.

**Costs accepted.** The Router locks logins out after 5 failed attempts
(`MAX_LOGIN_COUNT`, in its JavaScript), and these jobs run unattended. So the
whole role is gated on `zte_router_enabled`, baked into the scripts at template
time. On a fresh install it stays `false` until `vault_zte_router_password` is
the real admin password.
