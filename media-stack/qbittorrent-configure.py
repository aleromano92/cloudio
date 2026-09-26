#!/usr/bin/env python3
"""Apply the desired qBittorrent settings through its web API.

Deployed next to docker-compose.yaml by ansible/roles/media_lxc and run in the
media LXC after every deploy:  qbittorrent-configure.py <settings.json>
The settings come from `qbittorrent_preferences` in group_vars/all/vars.yml.

The API is reached with `docker exec qbittorrent curl` against localhost inside
the container, where qBittorrent can skip its login ("bypass authentication
for clients on localhost"), so no WebUI password is involved. A brand-new
qBittorrent has that off; if the API refuses, it is switched on in the config
file with the container stopped (qBittorrent rewrites the file whenever it
exits, so editing it while running is lost) and the call is retried.

Only settings that differ are sent. Prints CHANGED <names> or UNCHANGED.
"""
import json
import re
import subprocess
import sys
import time

CONTAINER = "qbittorrent"
CONF = "/opt/appdata/qbittorrent/qBittorrent/qBittorrent.conf"
API = "http://localhost:8080/api/v2"
TOGETHER = [("schedule_from_hour", "schedule_from_min"), ("schedule_to_hour", "schedule_to_min")]


def curl(*args):
    r = subprocess.run(["docker", "exec", CONTAINER, "curl", "-s", "-w", "\n%{http_code}", *args],
                       capture_output=True, text=True)
    body, _, code = r.stdout.rpartition("\n")
    return int(code) if code.strip().isdigit() else 0, body


def current():
    """The live settings, or None if the API demands a login."""
    for _ in range(45):
        code, body = curl(f"{API}/app/preferences")
        if code == 200:
            return json.loads(body)
        if code in (401, 403):
            return None
        time.sleep(2)  # not up yet: a fresh container needs a few seconds
    sys.exit("qBittorrent's API did not come up")


def allow_localhost_api():
    subprocess.run(["docker", "stop", CONTAINER], check=True, capture_output=True)
    with open(CONF) as f:
        text = f.read()
    text = re.sub(r"(?m)^WebUI\\LocalHostAuth=.*\n?", "", text)
    if re.search(r"(?m)^\[Preferences\]$", text):
        text = re.sub(r"(?m)^\[Preferences\]\n", "[Preferences]\nWebUI\\\\LocalHostAuth=false\n", text, count=1)
    else:
        text += "\n[Preferences]\nWebUI\\LocalHostAuth=false\n"
    with open(CONF, "w") as f:
        f.write(text)
    subprocess.run(["docker", "start", CONTAINER], check=True, capture_output=True)


with open(sys.argv[1]) as f:
    want = json.load(f)

changed = []
prefs = current()
if prefs is None:
    allow_localhost_api()
    changed.append("localhost API access")
    prefs = current()
    if prefs is None:
        sys.exit("qBittorrent still refuses the API after allowing localhost access")

diff = {k: v for k, v in want.items() if prefs.get(k) != v}
# qBittorrent only takes a schedule time with its hour and minute in the same
# request; an hour on its own is silently ignored.
for pair in TOGETHER:
    if any(k in diff for k in pair):
        diff.update({k: want[k] for k in pair if k in want})
if diff:
    code, body = curl("--data-urlencode", "json=" + json.dumps(diff), f"{API}/app/setPreferences")
    if code != 200:
        sys.exit(f"setPreferences failed: HTTP {code} {body}")
    after = current()
    rejected = {k: after.get(k) for k in diff if after.get(k) != want[k]}
    if rejected:
        sys.exit(f"qBittorrent did not keep: {rejected}")
    changed += sorted(diff)

print("CHANGED " + ", ".join(changed) if changed else "UNCHANGED")
