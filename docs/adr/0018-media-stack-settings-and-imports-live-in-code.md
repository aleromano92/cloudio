# 0018 — The media stack: settings and import rules live in code

Applies to: `media-stack/`, the `media_lxc` role, and the `media_*` and
`qbittorrent_preferences` variables. The README's "Media stack" covers the
drive layout, the seeding policy and its bufferbloat measurements. ADR-0010 and
ADR-0011 cover Caddy and the forwarded port.

**Image tags.** Sonarr, Radarr, Lidarr and Prowlarr run `latest` and update
themselves. Every Sunday at 05:00, `cloudio-media-update.timer` on pve pulls
their images and recreates them, then prunes the old images
(`media_auto_update_services`, `media_auto_update_on_calendar`).
- The user chose this on 2026-11-21, over pinned tags bumped by hand. Their
  settings pages kept saying an update was waiting: in Docker their own
  updater is off, so only a new image updates them.
- Major versions arrive unannounced too, and their database migrations go one
  way only. The rollback is the nightly backup of the LXC, taken at 02:30
  that same night.
- The run is a plain timer on pve, not Ansible: the vault password is never
  stored on the node (ADR-0022), so no playbook runs unattended. The repo
  holds `latest`, so the next playbook run never downgrades an app whose
  database has already migrated.
- The other images stay pinned and are bumped deliberately.

**Networking.** Jellyfin runs on host networking, and so does Caddy in front of
it.
- Jellyfin's client discovery (7359/udp broadcast) and DLNA (1900/udp
  multicast) don't cross Docker's bridge.
- On the bridge, Jellyfin would see Docker's addresses instead of its clients'.
  Those addresses decide who counts as local.
- The LXC has its own IP, so both listen on `192.168.7.12` directly. Caddy
  reaches Jellyfin on `127.0.0.1`. Caddy takes 443 (forwarded) and 80 (LAN
  only).
- Caddy answers only the names in its config; any other name gets no
  certificate and no answer.

**The `.local` names.** At home each web UI also answers on
`http://<app>.local`, which the README lists.
- The LXC announces them over mDNS with Avahi, one `cloudio-mdns-alias@<name>`
  unit each. They are published without a reverse record (`--no-reverse`), so
  the six names don't each claim the address's reverse record, which
  `media.local` already holds.
- Avahi listens on `eth0` only. Left alone, it also announces Docker's bridge
  addresses.
- The role reads the names from the Caddyfile's `http://<name>.local` blocks,
  so the two lists can't drift apart.
- Caddy strips `X-Forwarded-For` before passing a request to Sonarr, Radarr,
  Lidarr or Prowlarr. Their current versions demand a login on any request
  that carries it, unless the proxy is in their Trusted Networks. Without the
  header, the request reaches them like a direct one from the LAN, which they
  let in without a login. The rule lives in the Caddyfile, not in four apps'
  settings.
- They are plain HTTP on port 80, which the router doesn't forward. mDNS
  doesn't cross Tailscale, so away from home the IP addresses are the way in.

**qBittorrent's settings go through its web API.** qBittorrent rewrites its
own config file on every exit, so that file can't be the source of truth.
`qbittorrent-configure.py` sends only the settings that differ. API facts it
depends on:
- Speeds are bytes/s, whatever the docs say: the factory alternative limit
  reads back as 10240. qBittorrent keeps whole KiB, so 100 Mbps is 12207 KiB/s,
  or 12499968.
- A schedule time is only accepted with its hour and minute in the same
  request. An hour sent on its own is silently ignored.
- The script calls the API from inside the container, where "bypass
  authentication for clients on localhost" skips the login. A brand-new
  qBittorrent has that off. The script turns it on in the config file with the
  container stopped (an edit made while it runs is lost) and retries.
- A fresh container's API needs a few seconds to come up.

**Seeding settings beyond the README's table.**
- Peer connections are capped at 200 overall and 50 per torrent, to spare the
  5G router's NAT table. About 80 peers were in use across 63 torrents on
  2026-11-10.
- The caps count protocol overhead (TCP and uTP), so they hold on the wire.
- The alternative upload limit equals the normal one, so the weekday schedule
  only caps download. The schedule runs in the container's timezone.
- UPnP is off; 6881 is forwarded by hand (ADR-0010).
- 500 files can be open at once, for a 107-file pack among 30+ torrents.

**arr-autoimport's matching rules.** These are deliberate, against wrong
imports:
- Trust only TMDB's best answer for the year (±1). A lower-ranked result that
  happens to be in the library is how a wrong film sneaks in.
- A franchise name before a 1, plus the year, is exact enough
  ("American Pie 1 Il primo assaggio" → "American Pie"). Any other number is
  dropped only before a subtitle ("American Pie 3 Il matrimonio" → "American
  Pie Il matrimonio"). Without its number, "Paranormal Activity 2" (2010)
  reads as "Paranormal Activity" (2009), which the ±1 year lets through. It
  was caught on 2026-11-21 in a dry run, before anything was imported.
- A title can carry an Italian and an English name, each with its own " - "
  subtitle ("Notte al Museo - Il Segreto del Faraone - Night at the Museum -
  Secret of the Tomb"). Every run of adjacent parts is tried, longest first,
  so the English pair is found.
- A pack holds several full films, so each file is matched on its own name.
  Files under 40% of the largest are extras, not films.
- When the torrent's name doesn't match, the main file's name is tried, since
  the torrent's may be vaguer.
- Sonarr's manual import is queried without `seriesId`. With it, Sonarr lists
  the series' library files instead of the download's.
