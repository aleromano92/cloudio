---
name: delete-comment
description: Sweep the comments still on the comment ratchet. Each is categorised and deleted; decisions move into ADRs and hacks become GitHub issues.
argument-hint: "[file or directory; default: the whole repo]"
disable-model-invocation: true
---

# Delete comments

Code in this repo carries no comments (ADR-0024). The comments that predate the
rule are listed in `tools/comment-ratchet.json`, the **ratchet**. This sweep
works through them. Each one ends up deleted, with any knowledge it held moved
to where it belongs. Scope: `$ARGUMENTS` if given, else the whole repo.

Work on a branch. Keep a **ledger** as you go, one row per comment: `path:line`,
the text, its category, its action and the destination.

## 1. Inventory

Run `tools/comment-ratchet.py --list` and filter it to the scope. Read every
file in the scope **in full**, plus the README and `docs/adr/`. A comment can
only be judged against the code around it and against what's already
written down.

Done when the ledger has a row for every comment in scope. A block of
consecutive comment lines is one comment.

## 2. Categorise

Give every comment exactly one category:

- **Tautology**: it says what the code, a name, the README or an existing ADR
  already says. Unit and port annotations, section banners, usage that the
  README documents, and function signatures restated above the function all
  count.
- **Stale**: it describes code, values, history or plans that no longer match
  the repo. Examples: "(was 500)", a finished experiment, a reference to a
  file or setup that's gone, a comment orphaned from the code it described.
  Grep every name it mentions to be sure.
- **Excuse**: it justifies a shortcut instead of fixing it. Examples:
  commented-out code kept "for later", "pin it when convenient", a hard-coded
  assumption with "adjust it if…", a one-time migration shim left running.
- **Decision record**: a non-obvious *why*. That means a constraint the code
  can't show, a deliberate deviation from the obvious path, an incident that
  set a value, or a rejected alternative.

Split a mixed comment. "(was 100): a 107-file pack among 30+ torrents" is
stale history plus a decision. A comment that fits none of the four stays on
the ratchet, and the ledger records why. So far these are operator
instructions in a template (`vault.yml.example`), usage for a script that
people run by hand, and a markup contract.

Done when every row has a category, and every decision has a destination:
the README or the ADR that already holds it, an ADR to extend, or a new ADR.

## 3. Act

- **Tautology, Stale**: delete it.
- **Excuse**: delete it, and file one GitHub issue per hack with
  `gh issue create`. Give it an imperative title that names the fix. The body
  says where it is (`path:line`), what the comment said, why it's a hack, and
  the fix. The repo is public: an issue carries no secrets, tokens or personal
  details. Search the open issues first, and add to a matching one instead of
  filing a duplicate.
- **Decision record**: if the README or an ADR already says it, delete it.
  Otherwise add it to the ADR whose "Applies to" line names the file (search
  with `grep -l '<file name>' docs/adr/`). If no ADR fits, write a new one: the
  next number, `# NNNN — Title`, an "Applies to:" line, the decision, the rules
  that follow from it, and the costs accepted. Write the reason, in the
  repo's voice, and keep dates and measurements.
- **A "what" that needs a comment** usually needs a better name. Rename the
  variable or function in the same change, everywhere it's used.

A one-line `# Managed by Ansible (<role>).` banner, a shebang and tool
directives (`shellcheck`, `noqa`) are not comments. Shorten a longer banner to
exactly that form. When a comment was the only thing inside a `{% if %}` block,
remove the block too.

Done when `tools/comment-ratchet.py --list` for the scope shows only the
comments the ledger keeps.

## 4. Prove that only comments changed

- `tools/comment-ratchet.py --compare master` must pass. Account for every
  file it reports as an intended change, such as an empty Jinja block or a
  rename.
- `cd ansible && ansible-playbook site.yml --syntax-check` must exit 0.
  Also run `bash -n` on the non-template shell scripts,
  `python3 -m py_compile` on the Python, and `node --check` on the JavaScript.
- Grep the README and `docs/` for `comment`, `uncomment` and `top of`, and fix
  every pointer to a comment that is gone.

Done when all of these pass.

## 5. Tighten the ratchet

Run `tools/comment-ratchet.py --update`, then `tools/comment-ratchet.py`, which
must print OK. Commit `tools/comment-ratchet.json` together with the deletions.

## 6. Report

- Counts per category, by file.
- The issues filed, as links.
- The ADRs created or extended.
- The comments kept, and why.
- Lines removed from code against lines added to `docs/adr/`.
- Which rendered files change on the hosts, so their handlers restart on the
  next playbook run (for example the watchdog, the power watch and NUT).
