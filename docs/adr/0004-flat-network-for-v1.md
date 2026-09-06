# 0004 — Flat network for v1; segmentation deferred

Every device — server, laptops, phones, TVs, Reolink cameras, IoT — sits on one
subnet for v1. Proper VLAN segmentation needs a device that can route and firewall
between VLANs, and the only router is a 5G LTE box that cannot. Making the Vaio the
house router was rejected: a 2-core laptop as a single point of failure for all
household internet. Segmentation is Phase 2 and depends on adding a UniFi gateway
or a dedicated OPNsense box. Interim mitigations: client isolation on the IoT SSID;
block the cameras/NVR from the internet at the switch.
