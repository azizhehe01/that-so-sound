# Surround and stabilizer card refinement

Scope: only `EffectArt` and the two upper effect-card bodies in `app/audio_ui.py`; no audio backend, shared theme, other card, or navigation changes.

Design direction: supporting desktop audio controls, existing pink-accent visual language. ENERGY 2 / RHYTHM 2 / MOTION 1, unchanged from UI-DESIGN.md.

Reasons:
- Equal-width cards retain equal functional importance and the existing layout.
- Shared 18px horizontal padding, header alignment and top-aligned descriptions connect the text to the illustration without moving controls.
- Existing effectTitle/caption typography preserves the interface hierarchy and shared contrast roles.
- Listener, elliptical waves and two speakers explain spatial sound; the fixed waveform explains amplitude stabilization.
- QPainter paths and shared accent/secondary/surface/border/muted tokens keep drawings crisp and theme-aware without new raster assets.
- Off-state art uses muted ink at 32% opacity; text remains readable. No timer, signal sampling, live numbers, animation or meter semantics are introduced.

Verification:
- First regression test failed on the previous art's mouse-event handling; passed after vector/decorative implementation.
- Alignment regression failed on vertically centered descriptions; passed after top alignment.
- Full unittest suite: 52 tests, no failures, one opt-in vendor archive test skipped.
- Both switches operated by keyboard in all four themes; values read back through the existing command queue into the test backend for off and on.
- Existing audio optimistic-write, failure/recovery, EQ and theme tests passed.
- Illustrations differ for on/off and disabled widgets, and repeated renders are identical (static).
- Equal card widths within one rounding pixel and label containment tested at 1060x720, 1280x800 and 1600x1000.
- Rendered and visually inspected all four themes, both states, at all three sizes: 24 paired-card renders. No clipped titles, text or artwork. Description starts align despite different wrapping.
- `git diff --check` passed.

Evidence: `/home/azhehe/.cache/nahimic-effect-cards/manifest.json` and `contact-1060.png`, `contact-1280.png`, `contact-1600.png` in the same directory. Full-window renders are also saved there. Rendering uses the real Qt widgets offscreen with an isolated settings file and a test audio backend. No live audio settings or installed application files were changed; this pass does not claim a live DSP or compositor interaction test.

Delivery gate:
- Hard gate PASS within this scoped desktop change: requested assets only, unchanged AA text roles, keyboard-operated working toggles, all theme/state/size render combinations checked.
- Purpose gate PASS: illustrations explain each effect; equal geometry is explicitly requested and preserves hierarchy.
- Liveliness PASS: pink active-state accent and spatial/waveform motifs distinguish the functions without competing with the EQ focal point; no decorative motion.
- Craftsmanship PASS: tested rendering, equal geometry, aligned text, disabled-state distinction, existing queue behavior preserved. No unrelated layout or audio changes.
