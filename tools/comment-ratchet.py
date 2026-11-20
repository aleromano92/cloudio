#!/usr/bin/env python3
"""The comment ratchet: code in this repo carries no comments.

Comments that predate the rule are listed in tools/comment-ratchet.json, and
that list only ever shrinks. A comment missing from it fails the check. So
does a listed comment that has gone, until --update drops it from the list,
so a deleted comment can't come back later.

  tools/comment-ratchet.py            check every file git knows about (CI)
  tools/comment-ratchet.py --update   drop the entries for comments that are gone
  tools/comment-ratchet.py --list     print every comment as path:line: text
  tools/comment-ratchet.py --compare master
                                      fail unless only comments changed since master

Not comments: a shebang, tool directives (shellcheck, noqa) and the one-line
"# Managed by Ansible (<role>)." banner rendered onto the hosts. Python
docstrings are documentation, not comments. Markdown and JSON are skipped.

Where a comment's knowledge goes instead: .claude/skills/delete-comment.
"""
import argparse
import difflib
import io
import json
import re
import subprocess
import sys
import tokenize
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BASELINE = ROOT / "tools" / "comment-ratchet.json"
SKIPPED_SUFFIXES = {".md", ".json", ".png", ".jpg", ".jpeg", ".gif", ".ico", ".svg", ".gz", ".pdf"}
INI_SUFFIXES = {".service", ".timer", ".cfg", ".ini"}
MARKER = re.compile(r"^#\s*(shellcheck\s|noqa\b|type:)|^# Managed by Ansible \([^)\n]*\)\.$")
BANNER = re.compile(r"^\s*# Managed by Ansible \(")
HTML_REGIONS = re.compile(
    r"<script\b[^>]*>(?P<js>.*?)</script>|<style\b[^>]*>(?P<css>.*?)</style>|<!--(?P<html>.*?)-->",
    re.DOTALL | re.IGNORECASE,
)


def tracked_files():
    out = subprocess.run(
        ["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
        cwd=ROOT, capture_output=True, check=True,
    ).stdout.decode()
    return sorted({p for p in out.split("\0") if p and (ROOT / p).is_file()})


def language(path):
    name = path[:-3] if path.endswith(".j2") else path
    suffix = Path(name).suffix
    if suffix == ".py":
        return "python"
    if suffix in {".html", ".htm"}:
        return "html"
    if suffix in {".js", ".mjs"}:
        return "js"
    if suffix == ".css":
        return "css"
    if suffix in INI_SUFFIXES:
        return "ini"
    return "hash"


def hash_start(line, jinja):
    quote = None
    i = 0
    while i < len(line):
        c = line[i]
        if quote:
            if c == "\\" and quote == '"':
                i += 2
                continue
            if c == quote:
                quote = None
        elif c == "\\":
            i += 2
            continue
        elif c == '"' or (c == "'" and not (i and line[i - 1].isalnum())):
            quote = c
        elif c == "#" and (i == 0 or line[i - 1] in " \t"):
            return i
        elif jinja and line.startswith("{#", i) and not (i and line[i - 1] == "$"):
            return i
        i += 1
    return None


def hash_comments(text, path, ini):
    jinja = path.endswith(".j2")
    in_jinja_comment = False
    for n, line in enumerate(text.splitlines(), 1):
        if in_jinja_comment:
            yield n, line.strip()
            in_jinja_comment = "#}" not in line
            continue
        stripped = line.lstrip()
        if ini and stripped.startswith(";"):
            yield n, stripped.rstrip()
            continue
        i = hash_start(line, jinja)
        if i is None:
            continue
        comment = line[i:].rstrip()
        if n == 1 and comment.startswith("#!"):
            continue
        if comment.startswith("{#") and "#}" not in comment:
            in_jinja_comment = True
        yield n, comment


def python_comments(text):
    tokens = tokenize.generate_tokens(io.StringIO(text).readline)
    for tok in tokens:
        if tok.type == tokenize.COMMENT and not (tok.start[0] == 1 and tok.string.startswith("#!")):
            yield tok.start[0], tok.string.rstrip()


def c_comments(text, first_line, line_comments):
    i, n, line, quote = 0, len(text), first_line, None
    while i < n:
        c = text[i]
        if c == "\n":
            line += 1
            if quote in ("'", '"'):
                quote = None
            i += 1
            continue
        if quote:
            if c == "\\":
                if i + 1 < n and text[i + 1] == "\n":
                    line += 1
                i += 2
                continue
            if c == quote:
                quote = None
            i += 1
            continue
        if c in "'\"`":
            quote = c
            i += 1
            continue
        if text.startswith("/*", i):
            end = text.find("*/", i + 2)
            end = n if end < 0 else end + 2
            for k, part in enumerate(text[i:end].split("\n")):
                if part.strip():
                    yield line + k, part.strip()
            line += text.count("\n", i, end)
            i = end
            continue
        if line_comments and text.startswith("//", i):
            end = text.find("\n", i)
            end = n if end < 0 else end
            yield line, text[i:end].strip()
            i = end
            continue
        i += 1


def html_comments(text):
    for m in HTML_REGIONS.finditer(text):
        kind = m.lastgroup
        start = m.start(kind)
        first_line = text.count("\n", 0, start) + 1
        body = m.group(kind)
        if kind == "html":
            for k, part in enumerate(body.split("\n")):
                if part.strip():
                    yield first_line + k, part.strip()
        else:
            yield from c_comments(body, first_line, line_comments=kind == "js")


def comments_in(path, raw=None):
    if Path(path).suffix in SKIPPED_SUFFIXES:
        return []
    if raw is None:
        raw = (ROOT / path).read_bytes()
    if b"\0" in raw or raw.startswith(b"$ANSIBLE_VAULT"):
        return []
    text = raw.decode("utf-8", errors="replace")
    lang = language(path)
    if lang == "python":
        found = python_comments(text)
    elif lang == "html":
        found = html_comments(text)
    elif lang == "js":
        found = c_comments(text, 1, line_comments=True)
    elif lang == "css":
        found = c_comments(text, 1, line_comments=False)
    else:
        found = hash_comments(text, path, ini=lang == "ini")
    return [(n, t) for n, t in found if not MARKER.match(t)]


def scan():
    return {path: found for path in tracked_files() if (found := comments_in(path))}


def load_baseline():
    if not BASELINE.exists():
        return {}
    return json.loads(BASELINE.read_text())


def write_baseline(entries):
    entries = {path: texts for path, texts in sorted(entries.items()) if texts}
    BASELINE.write_text(json.dumps(entries, indent=2, ensure_ascii=False) + "\n")


def compare(current, baseline):
    new, gone = [], []
    for path in sorted(set(current) | set(baseline)):
        found = current.get(path, [])
        allowed = Counter(baseline.get(path, []))
        extra = Counter(t for _, t in found) - allowed
        for n, text in found:
            if extra[text]:
                extra[text] -= 1
                new.append((path, n, text))
        missing = allowed - Counter(t for _, t in found)
        gone.extend((path, text) for text in missing.elements())
    return new, gone


def code_lines(path, raw):
    lines = raw.decode("utf-8", errors="replace").split("\n")
    for n, text in comments_in(path, raw):
        line = lines[n - 1]
        lines[n - 1] = "" if line.strip() == text else line.rstrip().removesuffix(text)
    return [
        line.rstrip()
        for n, line in enumerate(lines, 1)
        if line.strip() and not BANNER.match(line) and not (n == 1 and line.startswith("#!"))
    ]


def git_show(ref, path):
    shown = subprocess.run(["git", "show", f"{ref}:{path}"], cwd=ROOT, capture_output=True)
    return shown.stdout if shown.returncode == 0 else None


def compare_to(ref):
    changed = subprocess.run(
        ["git", "diff", "--name-only", ref, "--"], cwd=ROOT, capture_output=True, text=True, check=True
    ).stdout.split()
    compared, differ = 0, 0
    for path in changed:
        before, here = git_show(ref, path), ROOT / path
        if Path(path).suffix in SKIPPED_SUFFIXES or before is None or not here.is_file():
            continue
        compared += 1
        old, new = code_lines(path, before), code_lines(path, here.read_bytes())
        if old != new:
            differ += 1
            print(f"== {path}: code changed, not only comments")
            for line in difflib.unified_diff(old, new, lineterm="", n=0):
                if not line.startswith(("---", "+++")):
                    print(line)
    if differ:
        print(f"\n{differ} of {compared} file(s) changed more than comments since {ref}.")
        return 1
    print(f"only comments changed in {compared} file(s) since {ref}")
    return 0


def report_new(new):
    for path, n, text in new:
        print(f"{path}:{n}: new comment: {text}")
    print(
        f"\n{len(new)} comment(s) not on the ratchet. Delete them: rename or restructure the code"
        "\nso it says the same thing, and put any decision behind it in docs/adr/"
        "\n(.claude/skills/delete-comment/SKILL.md walks through it)."
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--update", action="store_true", help="drop entries for comments that are gone")
    mode.add_argument("--list", action="store_true", help="print every comment as path:line: text")
    mode.add_argument("--init", action="store_true", help="write the first baseline (refuses if one exists)")
    mode.add_argument("--compare", metavar="REF", help="fail unless only comments changed since the git ref")
    args = parser.parse_args()

    if args.compare:
        return compare_to(args.compare)

    current = scan()

    if args.list:
        for path, found in current.items():
            for n, text in found:
                print(f"{path}:{n}: {text}")
        print(f"{sum(map(len, current.values()))} comment line(s) in {len(current)} file(s)", file=sys.stderr)
        return 0

    if args.init:
        if BASELINE.exists():
            print(f"{BASELINE.relative_to(ROOT)} already exists; the ratchet only tightens (--update).", file=sys.stderr)
            return 1
        write_baseline({path: [t for _, t in found] for path, found in current.items()})
        print(f"wrote {BASELINE.relative_to(ROOT)}")
        return 0

    baseline = load_baseline()
    new, gone = compare(current, baseline)

    if args.update:
        if new:
            report_new(new)
            return 1
        write_baseline({path: [t for _, t in found] for path, found in current.items()})
        print(f"ratchet tightened by {len(gone)} comment(s)" if gone else "ratchet already tight")
        return 0

    if new:
        report_new(new)
    if gone:
        for path, text in gone:
            print(f"{path}: comment gone, still on the ratchet: {text}")
        print(
            f"\n{len(gone)} comment(s) deleted: run tools/comment-ratchet.py --update and commit"
            " tools/comment-ratchet.json, so they can't come back."
        )
    if new or gone:
        return 1
    print(f"comment ratchet: OK ({sum(map(len, baseline.values()))} comment(s) left to delete)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
