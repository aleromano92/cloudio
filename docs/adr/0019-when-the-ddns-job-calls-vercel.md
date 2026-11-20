# 0019 — When the DDNS job calls Vercel

Applies to: the `ddns` role and the `ddns_*` variables. ADR-0010 records why the
home IP is published at all, and the 60 s check.

**Decision.** Each run finds the public IP and brings every name in
`ddns_records` to it as an A record. Vercel is called only when the IP differs
from the one last set, plus once every 30 minutes in case a record was edited
by hand. `--force` always asks Vercel.

**Rules that follow from it.**
- The public IP comes from three independent services, so one being down
  doesn't stop an update.
- No public IP means no uplink. That isn't an error here: the watchdog owns
  outages (ADR-0014).
- The TTL is 60 s, Vercel's minimum. It bounds how long a client can cache a
  stale IP.
- One name failing doesn't stop the others. The IP isn't recorded as done,
  though, so the next run retries them all.
- `ddns_on_ip_change` fires on the job's own record of the last IP it acted on,
  not on the DNS state. That way a Vercel outage neither delays it nor makes it
  fire every minute until Vercel is back. It doesn't fire on the very first run,
  and a failed hook is retried on the next.
- The playbook runs the job once with `--force`. A wrong token, scope or team id
  therefore fails the playbook, instead of failing silently every minute
  afterwards.
