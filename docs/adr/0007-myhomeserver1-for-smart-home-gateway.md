# 0007 — MyHOMEServer1 as the MyHOME ↔ Home Assistant gateway

The wired BTicino MyHOME (SCS bus) is bridged to Home Assistant with a single
**MyHOMEServer1**, chosen over the current-generation split (F460 for the app +
F461 for OpenWebNet) and over F461-alone. Rationale: MyHOMEServer1 exposes **both**
the MyHOME_Up app and a local **OpenWebNet** API from one device, it is the
most-proven gateway with the HA OpenWebNet (HACS) integration, and one box is
cheaper and simpler for this build. Trade-offs: it is previous-generation — source
it new with warranty; the HA path is fully local, so Legrand ending support does
not break it — and its app is MyHOME_Up, not Home + Control. The originally
spec'd F460 does not speak OpenWebNet at all, so it was never an option here.
