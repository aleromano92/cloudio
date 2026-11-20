# 0018 — The media stack: settings and import rules live in code

Applies to: `media-stack/`, the `media_lxc` role, and the `media_*` and
`qbittorrent_preferences` variables. The README's "Media stack" covers the
drive layout, the seeding policy and its bufferbloat measurements. ADR-0010 and
ADR-0011 cover Caddy and the forwarded port.

**Image tags are pinned** and bumped deliberately, never by a pull of `latest`.

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
- A franchise name before a number, plus the year, is exact enough
  ("American Pie 1 Il primo assaggio" → "American Pie").
- A pack holds several full films, so each file is matched on its own name.
  Files under 40% of the largest are extras, not films.
- When the torrent's name doesn't match, the main file's name is tried, since
  the torrent's may be vaguer.
- Sonarr's manual import is queried without `seriesId`. With it, Sonarr lists
  the series' library files instead of the download's.
