# Audio panel design

## Direction

The supplied desktop reference is the source of direction: a left navigation rail, horizontal listening profiles, an equalizer as the main focal point, output controls alongside it, and subordinate effect controls below. ENERGY 2 / RHYTHM 2 / MOTION 1.

- Layout: keep the equalizer and speaker volume visible together so tuning does not require alternating between a modal and the main window.
- Spacing: larger outer margins establish the page boundary; smaller, consistent gaps group controls within each effect.
- Typography: native sans-serif text preserves desktop legibility; headings and numeric gains establish hierarchy without decorative display fonts.
- Panels: each bounded surface represents an independently adjustable audio function, rather than a decorative dashboard metric.
- Pink accent: identifies selected profiles and active controls, matching the supplied reference.
- Artwork: reuse existing community branding rather than inventing a new identity.
- EQ curve: visualize the actual ten gain controls, not an invented spectrum or live audio measurement.
- Output: describe the real speaker target; do not imply that unsupported device switching is available.
- Motion: immediate control feedback and focus/hover states only; no looping decorative animation.

## Appearance

Settings > Appearance > Color Theme offers four whole-interface palettes:

- Rosé: light pink root, blush surfaces, dark plum text.
- Midnight Rose: dark burgundy root, mauve surfaces, pink controls.
- Dark: charcoal root, gray surfaces, pink controls.
- Light: white root, light gray surfaces, pink controls.

Theme roles include root, navigation, panels, alternate surfaces, primary/secondary text, boundaries, focus, selection, disabled controls, slider tracks, switch thumbs and chart strokes. Applying a theme must repaint custom-drawn widgets as well as Qt-styled controls. Appearance persists independently of audio parameters and must not restart the audio service.

## Verification boundaries

Unit/UI tests run with an isolated settings directory and a test audio backend. They do not prove live DSP operation. Live checks use the installed MSI service and OEM profile, must read back the actual effect values, and restore changed audio settings. Successful control readback does not constitute a subjective listening-quality assessment.

## Run the source checkout with the existing MSI installation

The local `nahimic-msi` launcher normally uses its installed copy, not this checkout. To run the redesigned source against that same installed runtime:

```sh
cd /home/azhehe/nahimic-linux-msi
NAHIMIC_SERVICE=nahimic-msi.service \
NAHIMIC_SHARE_DIR=/home/azhehe/.local/share/nahimic-msi/runtime \
python3 app/main.py
```

Close an already-open panel first: the single-instance lock otherwise brings that existing window forward. Closing the panel does not stop the audio service. This command does not reinstall or replace the OEM runtime.
