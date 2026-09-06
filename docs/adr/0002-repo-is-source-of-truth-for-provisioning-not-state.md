# 0002 — The repo is the source of truth for provisioning, not runtime state

The repo holds only Config: how to create the VM, the containers, and the services.
Runtime State (Home Assistant's config after UI edits, the *arr databases, UniFi's
MongoDB) is never committed — it is captured by backups instead. Rationale: that
state is large, binary, secret-laden and changes constantly, and every app fights
an import/export pipeline. Consequence: a working, tested backup routine is
mandatory, not optional (local `vzdump` + off-site `restic` to a Hetzner Storage
Box — see README) — without it a hardware migration becomes a multi-day
hand-rebuild.
