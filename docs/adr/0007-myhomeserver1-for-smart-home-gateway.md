# 0007 — MyHOMEServer1 as the MyHOME ↔ Home Assistant gateway

> **Status: BLOCKED / likely superseded (2026-09-10).** MyHOMEServer1 turned out
> to be out of production, and the installer fitted the originally-spec'd **F460**
> without consulting — which does *not* speak OpenWebNet. F460 + F461 is
> forbidden by BTicino (mutually exclusive, per their catalog). Leading option:
> replace the F460 with an **F461** (OpenWebNet server, no BTicino app — HA
> becomes the only interface). A future ADR will record the final decision.
> Earlier note in this ADR that F461 pairs alongside an F460 was wrong.

The wired BTicino MyHOME (SCS bus) is bridged to Home Assistant with a single
**MyHOMEServer1**, chosen over the current-generation split (F460 for the app +
F461 for OpenWebNet) and over F461-alone. Rationale: MyHOMEServer1 exposes **both**
the MyHOME_Up app and a local **OpenWebNet** API from one device, it is the
most-proven gateway with the HA OpenWebNet (HACS) integration, and one box is
cheaper and simpler for this build. Trade-offs: it is previous-generation — source
it new with warranty; the HA path is fully local, so Legrand ending support does
not break it — and its app is MyHOME_Up, not Home + Control. The originally
spec'd F460 does not speak OpenWebNet at all, so it was never an option here.
