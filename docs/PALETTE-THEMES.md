# Screenshot palette themes

Source: `/home/azhehe/Pictures/Screenshots/screenshot_2026-10-11_21-45-11.png`.
Colors sampled from the solid interiors of each band, not anti-aliased edges.
Order is left-to-right, then top-to-bottom. Within each palette, colors are listed top-to-bottom.

| Theme | Color 1 | Color 2 | Color 3 | Color 4 |
|---|---|---|---|---|
| Ocean Sand | #086288 | #4d8dba | #97d7ff | #ffefc4 |
| Citrus Grove | #d98327 | #ece8af | #4a943e | #186049 |
| Marigold Chili | #4f7d32 | #ffd16a | #f5b52e | #d9361e |
| Blush Sage | #f6e2e9 | #fefaf3 | #b8cfb3 | #84a282 |
| Coral Mint | #de7272 | #ffca88 | #fff6a9 | #b4e4d6 |
| Amber Espresso | #fef3e2 | #f4ae52 | #d4621a | #2a1a0e |
| Lagoon Lemon | #287a74 | #55a9a0 | #aeeed3 | #fff8b0 |
| Aqua Papaya | #8ad6d1 | #359fa0 | #fff0c5 | #ff8c52 |
| Woodland Sage | #5c7057 | #89a482 | #acc5a6 | #d1edd3 |
| Honey Olive | #fcf0da | #aeac78 | #f2c46a | #4c4541 |
| Terracotta Peach | #a14646 | #da6556 | #eb895b | #fdb773 |
| Orchid Petal | #8e1ea2 | #c654c3 | #ed96d7 | #ffc0de |

The original Rosé, Midnight Rose, Dark and Light remain first in the selector.
Source swatches are opaque and retain their colors even when the selector row is selected or disabled.

## Implementation and verification

- All 12 themes use exact source colors as opaque root, navigation, card and inset fills. Marigold Chili uses chili red for the selected profile; its inset is a supporting shade so body text remains readable.
- Body and navigation have separate semantic text/focus roles. This avoids forcing a single foreground onto both dark chrome and bright content.
- Derived shades supply text, disabled ink, borders, tracks, hover, focus, success and error states. The palette is applied through QSS, QPalette and custom-drawing tokens, not a global color overlay.
- Existing four theme dictionaries and resulting stylesheet strings were compared against the pre-change version and are identical. A regression hash protects the original dictionaries.
- The selector contains 16 themes. All 12 new four-swatch previews were pixel-checked in normal, selected and disabled icon modes: 144 exact-color checks.
- Rendered root, sidebar and card pixels match their exact opaque semantic fill values in all 12 themes. The app logo pixmap remains unchanged.
- Main window, Settings and theme popup were visually inspected for every new theme. The audit found low-contrast native titlebar icons; scoped native palettes fixed that issue and a regression test verifies all titlebar buttons.
- 48 render files cover 12 themes, each with a 1280x900 active window, 1060x720 disabled window, Settings and selector. Small-window layout is additionally covered by existing geometry tests.
- All 16 theme choices were saved and read in fresh interpreter processes, preserving the independent language preference. Selection applies immediately to existing widgets and Settings.
- Audio regression tests pass, including keyboard-operated surround/stabilizer switches in all 16 themes, EQ adjustment, command queue ordering and error recovery. Theme selection causes no audio writes. No live DSP or subjective listening retest was performed.
- Final full suite: 59 tests run, zero failures, one optional vendor-archive test skipped. `make -j4` and `git diff --check` passed.

Evidence: `/home/azhehe/.cache/nahimic-palette-expansion/` contains the per-theme PNGs, `renders.json`, and `audit-1.png` through `audit-4.png`. The renders use real Qt widgets, isolated preferences and a test audio backend. Installed files and personal audio settings were not modified.

Delivery gate: functional/contrast PASS (tests and rendered-pixel checks); source fidelity PASS (48 sampled colors and exact surface fills); visual consistency PASS (all 12 main windows and dialogs inspected); identity/layout preservation PASS (no layout or logo changes, original theme styles unchanged).

Design direction: retain the desktop audio workbench and its existing ENERGY 2 / RHYTHM 2 / MOTION 1. Source colors belong on actual surfaces and controls; supporting shades serve readable text, clear boundaries and focus rather than a global tint. No layout changes or logo recoloring are intended.
