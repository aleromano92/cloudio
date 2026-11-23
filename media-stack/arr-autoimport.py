#!/usr/bin/env python3
"""Import the downloads Radarr and Sonarr can't match on their own.

Runs in the media stack as the `arr-autoimport` service. Radarr and Sonarr
watch qBittorrent's `movies` and `tv` categories, but a hand-picked Italian
release ("X-Men - Giorni di un Futuro Passato - ROGUE CUT (2014) ...") parses
to a title neither app knows, so it waits forever as "manual import required".

Sonarr also blocks multi-season packs: it reads "Euphoria.S01-03..." as
season 1 only and rejects every 2x01 or 3x01 file as unexpected. And anime
packs count episodes from the first one ever aired: "Jujutsu Kaisen S02E25"
is season 2's first episode, "Ep 13" is season 1's thirteenth.

Every INTERVAL seconds this looks at each app's queue, including the items it
couldn't tie to a film or series and blocked series imports, and for every
finished one:

  1. cleans the parsed title (edition words like ROGUE CUT, EXTENDED, ...);
  2. finds the film/series in the library by title, original title or any
     alternate title (with the year, for films), else asks TMDB/TVDB through
     the app's own lookup and adds the result unmonitored, with no search;
  3. imports it through the app's ManualImport, which renames it, hardlinks
     it (qBittorrent keeps seeding) and replaces the old file.

It never replaces a file with one of equal or lower resolution, and never
monitors or searches anything: the user picks every release by hand.
Anything it can't place is left alone and logged once an hour.

API keys are read from the apps' own config.xml (mounted read-only).
"""
import json
import os
import re
import sys
import time
import unicodedata
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

INTERVAL = int(os.environ.get("INTERVAL", "120"))
RETRY_AFTER = 3600
DRY_RUN = os.environ.get("DRY_RUN") == "1"
VIDEO = (".mkv", ".mp4", ".avi", ".m4v", ".ts", ".wmv")

EDITION = re.compile(
    r"(?i)\b(rogue cut|extended( cut| edition| version)?|director'?s cut|"
    r"theatrical( cut)?|final cut|ultimate( edition| cut)?|special edition|"
    r"remastered|uncut|unrated|versione (estesa|integrale|cinematografica)|"
    r"edizione (speciale|estesa)|imax( edition)?|criterion|anniversary edition)\b"
)
SERIES_TAIL = re.compile(r"(?i)(?:[\s._-]+(?:s\d{1,2}|ep))+$")


def log(*a):
    print(time.strftime("%Y-%m-%d %H:%M:%S"), *a, flush=True)


def norm(s):
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode().lower()
    s = s.replace("&", " and ")
    return re.sub(r"[^a-z0-9]+", " ", s).strip()


def clean_title(t):
    t = EDITION.sub(" ", t or "")
    return re.sub(r"[\s\-:._]+$", "", re.sub(r"\s{2,}", " ", t)).strip(" -")


def series_name(t):
    """A series title as Sonarr parsed it, without the season or "Ep" that
    stuck to it: "Jujutsu Kaisen S01", "Jujutsu Kaisen - Ep"."""
    t = clean_title(t)
    return clean_title(SERIES_TAIL.sub("", t)) or t


class App:
    def __init__(self, name, port, kind):
        self.name, self.kind = name, kind
        key = ET.parse(f"/config/{name}/config.xml").getroot().findtext("ApiKey")
        self.base = f"http://{name}:{port}/api/v3/"
        self.key = key

    def api(self, path, data=None, params=None):
        url = self.base + path + ("?" + urllib.parse.urlencode(params) if params else "")
        req = urllib.request.Request(
            url,
            headers={"X-Api-Key": self.key, "Content-Type": "application/json"},
            data=json.dumps(data).encode() if data is not None else None,
        )
        with urllib.request.urlopen(req, timeout=300) as r:
            return json.load(r)


def video_items(items):
    v = [i for i in items if i["path"].lower().endswith(VIDEO) and "sample" not in i["path"].lower()]
    return sorted(v, key=lambda i: -i.get("size", 0))


def res_of(q):
    return ((q or {}).get("quality") or {}).get("resolution") or 0


def readings(title):
    """Ways to read a release title, most specific first.

    "American Pie 3 Il matrimonio - Wedding" -> the whole thing, each side of
    " - ", and each of those without the stray sequel number, which throws
    TMDB's search off ("American Pie Presents 1 Band Camp" finds nothing,
    "American Pie Presents Band Camp" does).

    With three or more parts, every run of adjacent parts is a reading too,
    longest first. "Notte al Museo - Il Segreto del Faraone - Night at the
    Museum - Secret of the Tomb" holds two titles with a " - " each, and
    only the run "Night at the Museum - Secret of the Tomb" is one TMDB knows.

    A 1 is always dropped, and what comes before it is the franchise's first
    film ("Kung Fu Panda 1" is "Kung Fu Panda"). Any other number is dropped
    only before a subtitle, which still names the sequel ("American Pie 3 Il
    matrimonio"). Without its number, "Paranormal Activity 2" (2010) would
    read as "Paranormal Activity" (2009), a year apart, and match it.
    """
    t = clean_title(title)
    parts = [p.strip() for p in t.split(" - ") if p.strip()] or [t]
    runs = [" - ".join(parts[i:i + n]) for n in range(len(parts), 0, -1) for i in range(len(parts) - n + 1)]
    out = []
    unnumbered = [re.sub(r"\s+(?:1|\d(?=\s+\S))\s+", " ", f" {p} ").strip() for p in runs]
    prefix = [re.split(r"\s1\s", f"{p} ")[0].strip() for p in runs if re.search(r"\s1\s", f"{p} ")]
    for p in runs + unnumbered + prefix:
        if p and p not in out:
            out.append(p)
    return out


def find_movie(radarr, title, year):
    cands = readings(title)
    if not cands:
        return None, "no title"
    wants = {norm(c) for c in cands}
    hits = []
    for m in radarr.api("movie"):
        names = {norm(m.get("title")), norm(m.get("originalTitle"))}
        names |= {norm(a.get("title")) for a in m.get("alternateTitles", [])}
        if wants & names and (not year or abs(m.get("year", 0) - year) <= 1):
            hits.append(m)
    if len(hits) == 1:
        return hits[0], "library"
    if len(hits) > 1:
        return None, f"{len(hits)} library films match"
    for c in cands:
        term = f"{c} {year}" if year else c
        best = [m for m in radarr.api("movie/lookup", params={"term": term})[:5]
                if not year or abs(m.get("year", 0) - year) <= 1][:1]
        for m in best:
            names = {norm(m.get("title")), norm(m.get("originalTitle"))}
            names |= {norm(a.get("title")) for a in m.get("alternateTitles", [])}
            if m.get("id"):
                return m, f"TMDB '{term}', already in library"
            if norm(c) in names:
                m.update(qualityProfileId=1, rootFolderPath="/data/media/movies", monitored=False,
                         minimumAvailability="released", addOptions={"searchForMovie": False, "monitor": "none"})
                if DRY_RUN:
                    return m, f"TMDB '{term}', would add"
                return radarr.api("movie", m), f"TMDB '{term}', added unmonitored"
    return None, f"no match for '{cands[0]}' ({year or 'no year'})"


def import_film(radarr, item, f, movie, how):
    old = (movie.get("movieFile") or {}).get("quality")
    if old and res_of(f["quality"]) <= res_of(old):
        return f"left alone: {res_of(f['quality'])}p is not better than the {res_of(old)}p already in {movie['title']}"
    langs = [l for l in (f.get("languages") or []) if l.get("id") not in (0, -1)] or [{"id": 5, "name": "Italian"}]
    if DRY_RUN:
        return f"would import into {movie['title']} ({movie['year']}) [{how}]"
    radarr.api("command", {"name": "ManualImport", "importMode": "auto", "files": [{
        "path": f["path"], "movieId": movie["id"], "quality": f["quality"], "languages": langs,
        "downloadId": item["downloadId"], "releaseGroup": f.get("releaseGroup")}]})
    return f"imported into {movie['title']} ({movie['year']}) [{how}]"


def parse_movie(radarr, name):
    p = radarr.api("parse", params={"title": name}).get("parsedMovieInfo") or {}
    return (p.get("movieTitles") or [p.get("movieTitle") or name])[0], p.get("year") or 0


def handle_movie(radarr, item):
    files = video_items(radarr.api("manualimport", params={"downloadId": item["downloadId"], "filterExistingFiles": "false"}))
    if not files:
        return "left alone: no video file in the download"
    films = [f for f in files if f.get("size", 0) >= 0.4 * files[0].get("size", 0)]
    if len(films) > 1:
        results = []
        for f in films:
            name = os.path.splitext(os.path.basename(f["path"]))[0]
            movie, how = find_movie(radarr, *parse_movie(radarr, name))
            results.append(f"{name[:50]}: " + (import_film(radarr, item, f, movie, how) if movie else f"left alone: {how}"))
        return f"pack of {len(films)} films\n    " + "\n    ".join(results)
    movie, how = find_movie(radarr, *parse_movie(radarr, item["title"]))
    if not movie:
        movie, how = find_movie(radarr, *parse_movie(radarr, os.path.splitext(os.path.basename(files[0]["path"]))[0]))
    if not movie:
        return f"left alone: {how}"
    return import_film(radarr, item, files[0], movie, how)


def find_series(sonarr, title):
    want = series_name(title)
    for s in sonarr.api("series"):
        names = {norm(s.get("title"))} | {norm(a.get("title")) for a in s.get("alternateTitles", [])}
        if norm(want) in names:
            return s, "library"
    for s in sonarr.api("series/lookup", params={"term": want})[:1]:
        if s.get("id"):
            return s, "TVDB, already in library"
    return None, f"no series in the library matches '{want}'"


def file_episodes(sonarr, f, series, have):
    """The library episodes a file holds, read from its own name.

    Sonarr's guess can't be trusted here: it ties a pack's files to what the
    folder name promised, so "Euphoria.S01-03..." expects season 1 only.

    A season and episode that don't exist are read as an absolute number,
    kept only if that episode is in the same season: "S02E25" is S02E01 when
    season 1 has 24 episodes. A name with only a number ("Ep 13") is that
    absolute episode.
    """
    if (f.get("series") or {}).get("id") == series["id"] and f.get("episodes"):
        return [e["id"] for e in f["episodes"]]
    name = os.path.splitext(os.path.basename(f["path"]))[0]
    p = sonarr.api("parse", params={"title": name}).get("parsedEpisodeInfo") or {}
    by_number = {(e["seasonNumber"], e["episodeNumber"]): e for e in have.values()}
    by_absolute = {e["absoluteEpisodeNumber"]: e for e in have.values() if e.get("absoluteEpisodeNumber")}
    season = p.get("seasonNumber")
    if p.get("episodeNumbers"):
        found = [by_number.get((season, n)) or by_absolute.get(n) for n in p["episodeNumbers"]]
        return [e["id"] if e and e["seasonNumber"] == season else None for e in found]
    if p.get("special"):
        return []
    return [(by_absolute.get(n) or {}).get("id") for n in p.get("absoluteEpisodeNumbers") or []]


def handle_episodes(sonarr, item):
    if item.get("seriesId"):
        series, how = sonarr.api(f"series/{item['seriesId']}"), "queue"
    else:
        parsed = sonarr.api("parse", params={"title": item["title"]}).get("parsedEpisodeInfo") or {}
        series, how = find_series(sonarr, parsed.get("seriesTitle") or item["title"])
    if not series:
        return f"left alone: {how}"
    items = video_items(sonarr.api("manualimport", params={
        "downloadId": item["downloadId"], "filterExistingFiles": "false"}))
    have = {e["id"]: e for e in sonarr.api("episode", params={"seriesId": series["id"], "includeEpisodeFile": "true"})}
    todo, skipped = [], 0
    for f in items:
        eps = [have.get(i) for i in file_episodes(sonarr, f, series, have)]
        if not eps or None in eps:
            skipped += 1
            continue
        if any(e.get("hasFile") and res_of(f["quality"]) <= res_of((e.get("episodeFile") or {}).get("quality")) for e in eps):
            skipped += 1
            continue
        langs = [l for l in (f.get("languages") or []) if l.get("id") not in (0, -1)] or [{"id": 5, "name": "Italian"}]
        todo.append({"path": f["path"], "seriesId": series["id"], "episodeIds": [e["id"] for e in eps],
                     "quality": f["quality"], "languages": langs, "downloadId": item["downloadId"],
                     "releaseGroup": f.get("releaseGroup")})
    if not todo:
        return f"left alone: none of {len(items)} files is an identifiable upgrade for {series['title']}"
    if not DRY_RUN:
        sonarr.api("command", {"name": "ManualImport", "importMode": "auto", "files": todo})
    verb = "would import" if DRY_RUN else "imported"
    return f"{verb} {len(todo)} episode file(s) into {series['title']} [{how}]" + (f", {skipped} left alone" if skipped else "")


def stuck(item, kind):
    """A finished download the app has not tied to a film/series itself, or a
    series pack it tied to only some of its seasons and so won't import."""
    if item.get("status") != "completed" or not item.get("downloadId"):
        return False
    if kind == "series" and item.get("trackedDownloadState") == "importBlocked":
        return True
    known = item.get("movieId") if kind == "movie" else item.get("seriesId")
    return not known


def main():
    apps = [(App("radarr", 7878, "movie"), handle_movie, {"includeUnknownMovieItems": "true"}),
            (App("sonarr", 8989, "series"), handle_episodes, {"includeUnknownSeriesItems": "true"})]
    tried = {}
    log("started", "(dry run)" if DRY_RUN else "", f"every {INTERVAL}s")
    while True:
        for app, handle, extra in apps:
            try:
                queue = app.api("queue", params={"pageSize": 200, **extra}).get("records", [])
            except Exception as e:
                log(app.name, "queue unavailable:", e)
                continue
            for item in queue:
                if not stuck(item, app.kind):
                    continue
                did = item["downloadId"]
                if time.time() - tried.get(did, 0) < RETRY_AFTER:
                    continue
                tried[did] = time.time()
                try:
                    log(app.name, item["title"][:100], "->", handle(app, item))
                except Exception as e:
                    log(app.name, item["title"][:100], "-> error:", e)
        if "--once" in sys.argv:
            return
        time.sleep(INTERVAL)


if __name__ == "__main__":
    main()
