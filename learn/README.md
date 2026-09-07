# learn/ — the cloudio course

A build-along course for understanding every concept this repo uses, starting with
Ansible. Static HTML, no build step.

**Start at [`index.html`](./index.html).**

## How to view it

- **Locally:** open `learn/index.html` in a browser. All links are relative, so it
  just works from disk.
- **GitHub Pages (rendered, shareable):** the `.github/workflows/pages.yml`
  workflow publishes this folder as the site root. One-time: repo
  Settings → Pages → Source → **"GitHub Actions"**. After that every push that
  touches `learn/` redeploys automatically. Live at
  `https://aleromano92.github.io/cloudio/`.
- Browsing the `.html` files directly on github.com shows their source, not the
  rendered page — use one of the two options above.

## Layout

| Path | What |
|---|---|
| `index.html` | course home — the lesson list |
| `lessons/NNNN-*.html` | the lessons, in order |
| `reference/*.html` | one-page printable references |
| `assets/` | shared stylesheet + quiz script (every lesson links these) |
| `MISSION.md` | why this course exists — steers what gets taught next |
| `RESOURCES.md` | the trusted sources lessons are built from |
| `GLOSSARY.md` | canonical terms (added as they're mastered) |
| `NOTES.md` | teaching preferences + session log |
| `learning-records/` | decision-grade notes on what's been learned (created lazily) |
