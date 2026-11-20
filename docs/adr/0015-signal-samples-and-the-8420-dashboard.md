# 0015 — Signal samples: an hourly grid, typed at collection, drawn on a static page

Applies to: `cloudio-signal-monitor.sh.j2` and its unit,
`cloudio-signal-digest.sh.j2`, `files/dashboard.html`, and the `signal_*` and
`ookla_*` variables.

**Sampling.**
- Samples run hourly at a fixed minute (:57), so they sit on a predictable
  grid. That matters for comparing the same hour across nights.
- A sample is the Router's readings plus one speedtest. It is best-effort: a
  failure in one half still logs the other.
- The sample is appended to `metrics.jsonl` *before* it is published to Home
  Assistant, so HA being unreachable can never cost the sample.
- Readings are typed at collection (numbers, or `null` when absent;
  ADR-0013). The digest and the dashboard therefore have one rule for "has a
  reading".
- The fields are chosen to explain a reading afterwards:
  - `cell_id`'s leading digits are the `enodeb_id` (the site). A change in
    `enodeb_id` means the modem moved to a different mast, not just a
    different sector.
  - `ngbr_cell_info` says whether a better cell existed at all.
  - `lte_band_lock` and `nr5g_band_lock` record the lock each sample was taken
    under.
  - The carrier-aggregation fields stay empty unless the lock allows more than
    one LTE band.

**The Ookla CLI's quirks.**
- It segfaults (`std::logic_error`, basic_string null construct) when `$HOME`
  is unset. That is true under a bare systemd unit but not over SSH, which is
  why it looked like an intermittent network failure until it was reproduced.
  The unit sets `HOME=/root`.
- Since 2026-10-13 the test server sometimes drops its socket mid-test
  (`Cannot read from socket`, exit 2). One retry after 20 s keeps that from
  costing the whole hour's sample.
- On first acceptance it prints its licence and GDPR banner on stdout. The JSON
  result is always the last line.

**The page on `:8420`.** It is static and served read-only by `npx serve`, with
no authentication: it shows read-only speedtest and signal numbers, nothing
sensitive. Its rules:
- **One definition per metric** (where it's read from, unit, colour,
  explanation, quality bands). Tiles, chart hints, threshold lines and the
  table all derive from it.
- **Quality bands:** a reading is fully green at `good`, fully red at `bad`,
  and blends through amber between them. The direction follows from the two
  numbers, so lower-is-better metrics need no flag.
- **Series colours are neutral**, blue then grey. Green, amber and red already
  mean good and bad on this page, so a line drawn in one of them would read as
  a verdict. The two were checked with the dataviz validator on the `#1a1a1a`
  chart surface: ΔE 26.8 for normal vision, 23.4 colour-blind.
- **Fixed, domain-meaningful axes.** Auto-scaling misrepresents proportion,
  and a flat reading auto-scaled to its own range draws a degenerate axis.
  Different units get separate charts, never a dual axis.
  - Upload's threshold lines (5 and 50) aren't drawn on the throughput axis,
    where they would sit within pixels of 0 and bury download's. Its
    thresholds still colour its tile and hint.
  - When charts share an axis but not thresholds, their hints name the metric.
- **Text readings are identity, not quantity.** They are never averaged or
  charted. Site and 4G cell together separate a move between sectors from a
  move between sites. The 5G cell moves throughput more than the 4G lock does
  (README), so locks are compared within one 5G cell.
- **Weeks run Monday to Sunday in the viewer's own timezone**, since that's
  how the nights being compared are experienced. Older weeks are logrotate's
  `.N.gz` files, fetched and inflated in the browser; a missing file ends the
  walk.
- **Ticks** fall at local midnight and midday, positioned by sample index,
  because the index is what the x axis is.
- **Hover** snaps to the nearest sample with a reading for that chart, so a
  failed run never blanks the tooltip. The tooltip is measured after it is
  shown (a hidden element has no size) and flipped to stay on screen. Info
  tips open downwards, because their icons sit at the top of the page. On the
  rightmost tiles they are anchored to the icon's right edge.
- **An outage** is everything from a watchdog `down` event to the `up` that
  closes it. The Router's state while it was down is shown with it. That is
  what separates "B1 switched off" from "modem wedged".

**The digest** is always written to a file. It is emailed only with
`signal_email_enabled`, which needs an SMTP relay.
