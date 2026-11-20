# 0024 — Code carries no comments; decisions live in ADRs

Comments in this repo had become the place where hacks were excused and
decisions were buried. Of 911 comment lines on 2026-11-20, most restated the
code or the README, some described code that had since changed, and a few
justified a shortcut instead of fixing it. The rest held real decisions, spread
across 70 files where nobody reviewing a change would look for them.

**Decision.** Code carries no comments:
- A decision goes into an ADR in `docs/adr/`, grouped by subsystem, with an
  "Applies to" line naming the files it governs.
- A hack gets a GitHub issue instead of an apology in the code.
- Anything that merely restates the code is deleted.

`tools/comment-ratchet.py` enforces this in CI (`.github/workflows/lint.yml`).
The comments that remain are listed in `tools/comment-ratchet.json`, and that
list only shrinks:
- A comment missing from the list fails the check.
- So does a listed comment that's gone, until `--update` drops it from the
  list, so a deleted comment can't come back.

`/delete-comment` (`.claude/skills/delete-comment/`) repeats the clean-up on
what's left.

**Not comments:**
- a shebang;
- tool directives (`shellcheck`, `noqa`);
- the one-line `# Managed by Ansible (<role>).` banner, which is rendered onto
  the hosts to warn whoever edits the file there;
- Python docstrings, which are documentation;
- Markdown and JSON, which aren't scanned.

**Costs accepted.**
- The reason for a line of code is one hop away: in the ADR its file is listed
  under, not next to it. `grep -l <file> docs/adr/` finds it.
- Fixing a typo in a comment still on the list fails the check. Delete the
  comment instead.
- Rendered files on the hosts lose their explanations too. Only the banner
  stays.
