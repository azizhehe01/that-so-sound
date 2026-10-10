# UI redesign verification

## Results

- `make -j4`: passed.
- `QT_QPA_PLATFORM=offscreen python3 -m unittest discover -s tests -q`: 50 tests run, no failures, one opt-in proprietary-archive test skipped.
- `git diff --check`: passed.
- Python compilation of application and new tests: passed.
- Static scan of changed application sources: no shell-injection, eval, pickle or hardcoded-secret matches.
- Independent code review: passed, with no security concerns or blocking logic errors. Reviewer independently exercised theme, layout and optimistic-UI tests.
- Backend and host source files are unchanged.

## Theme acceptance

All four palettes apply through shared semantic roles to the main window, panels, dialog, native popup palettes, custom-painted toggles, icons, EQ plot, window buttons, focus and disabled states.

- Rosé: PASS. Light pink background, blush panels, plum text.
- Midnight Rose: PASS. Burgundy background, mauve panels, pink accents.
- Dark: PASS. Charcoal background, gray panels, pink accents.
- Light: PASS. White background, light gray panels, pink accents.
- Immediate application: PASS. Existing window/dialog palettes and custom-painted widget tokens checked after every selection.
- Persistence: PASS. Each theme saved in one interpreter and loaded in a separate interpreter, retaining the independent English language preference.
- Offline appearance: PASS. Theme selection remains available when audio controls are disabled and causes no audio writes.
- Failed save: PASS. Simulated write failure retains the previous selector and displayed palette and raises a user-visible warning.
- Contrast: PASS. Primary, secondary, muted and accent text exceed 4.5:1 on all five relevant surfaces in every theme. Minimum ratios: Rosé 4.71, Midnight Rose 4.90, Dark 4.99, Light 4.93. Selected text exceeds 6.6:1.

## Layout and interaction evidence

- Rendered every theme at 1440 × 900 and the minimum 1060 × 720. Settings renders produced for every theme.
- A failing test reproduced EQ slider/frequency overlap at minimum size. The fix preserves a minimum tuning-panel height and lets shorter windows scroll, rather than compress labels.
- Minimum-size geometry checks verify EQ slider/frequency separation, long real output-name height, access to the bottom treble control through scrolling, and no horizontal scroll range.
- Settings navigation opens the dialog; Escape closes it.
- Keyboard Right changes an EQ band and sends the resulting value through the existing command queue.
- Existing tests still cover delayed replies, rapid coalesced edits, profile ordering barriers, rejected profile/parameter writes, drag protection and stale system acknowledgements.
- Offscreen rendering emits only the expected platform warning that `raise()` is unsupported. A native Qt panel was also launched against the live service. Desktop capture could not discover its Wayland window; native compositor mouse/drag behavior is not claimed as verified.

## Live audio integration

The source-tree Qt Panel was connected to the existing `nahimic-msi.service`, not a test audio backend. Speakers were muted during parameter changes. Twenty-six recorded checks passed:

- Mute control: actual speaker mute read back.
- Music, Movie, Communication and Gaming buttons: each actual selected profile read back.
- EQ, surround, compressor, voice, bass and treble switches: each toggled, read back, restored and read back.
- Every EQ band (31, 62, 125, 250, 500 Hz; 1, 2, 4, 8, 16 kHz): gain changed and read back, then restored.
- Voice, bass and treble gain sliders: changed and read back, then restored.
- Master volume: changed on the physical speaker sink and read back.
- Master effects: toggled on the real service and read back, then restored.

Restoration was verified by exact settings comparison and exact raw per-channel sink-volume comparison. Final volume was 49%, mute off, effects enabled, ready and active. The service instance was unchanged. No TWS tuning or routing code was changed. Autostart was not toggled on the live machine. This is control integration verification, not a subjective listening-quality test or an audio-service cold-restart test.

## Delivery gate

- Hard gates: PASS within the desktop scope above. Working controls, real parameter data, AA text roles, persisted complete themes and executable tests; no invented meters, statistics, testimonials or navigation destinations.
- Purpose gates: PASS. Color, layout, typography, panels, assets and motion reasons are recorded in `UI-DESIGN.md`; EQ fill communicates gain area, not decorative background glow.
- Liveliness: PASS. ENERGY 2 / RHYTHM 2 / MOTION 1; inline equalizer is the focal point, pink marks selection, space separates tuning from supporting effects.
- Craftsmanship: PASS for implemented desktop functionality. Bounded small-window layout, state/error handling, theme isolation and live control readback are verified. Native compositor drag/resize testing remains outside the verified scope.

The checkout is modified; the existing installed launcher/runtime was not overwritten. See `UI-DESIGN.md` for the source launch command.
