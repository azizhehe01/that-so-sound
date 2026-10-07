# Nahimic Linux — MSI/Fedora adaptation

A source adaptation of [wearzdk/nahimic-linux](https://github.com/wearzdk/nahimic-linux), based on upstream commit `6d8a826` (v0.3.0). This fork adds MSI GF63 Thin 11UCX speaker support and a portable local installation path. It is not an official Nahimic, MSI, SteelSeries, or Fedora release.

The application connects the original proprietary Nahimic APO4 runtime to PipeWire using Wine. It does **not** reimplement Nahimic's DSP. The Qt panel provides profile, bass, voice, treble, surround, volume stabilization, and equalizer controls.

## Hardware and verification limits

- MSI GF63 Thin 11UCX / MS-16R6: Realtek ALC897, codec `10ec0897`, subsystem `1462134c`. Uses the matching OEM `1462134C_InternalSpeakers.nsx`, not the MECHREVO speaker preset.
- Upstream MECHREVO Wujie 14X Pro: Senary `14f11f87`, subsystem `1d05e022`; original support is retained.
- Unknown codecs, subsystems, and headphone ports are rejected. Do not rename another model's settings to bypass validation.

The MSI adaptation has been exercised locally on Fedora with stereo speaker playback, OEM profile import, parameter readback, and service stop/restart. GUI integration and unit tests have also been exercised. Bluetooth/HDMI hotplug, long-duration reliability, and other machines are **not** established by those tests. Windows-identical acoustic quality is not guaranteed.

## Fedora build dependencies

```sh
sudo dnf install wine mingw64-gcc-c++ python3-pyside6 pulseaudio-libs-devel gcc make pkgconf-pkg-config cabextract
make -j4
python3 -m unittest discover -s tests -v
```

Requires x86_64 Linux, PipeWire Pulse, WirePlumber 0.5+, and a systemd user session. Python GUI dependencies must be available to the interpreter used by the launcher.

## Vendor components (not included)

Source publication deliberately excludes downloaded `.exe`, `.dll`, `.cab`, `.nsx`, and machine state. Community code is MIT; proprietary runtime, OEM configuration, and artwork retain their own terms. See [LICENSE](LICENSE), [packaging/LicenseRef-Nahimic](packaging/LicenseRef-Nahimic), and [app/assets/NOTICE.txt](app/assets/NOTICE.txt).

Fetch fixed official archives and verify checksums before extracting:

```sh
python3 scripts/fetch-runtime.py --hardware msi-gf63-11ucx --output runtime
```

The fetcher does not execute the Windows restore installer. For offline extraction from archives you already downloaded:

```sh
python3 packaging/extract_runtime.py /path/to/nahimic-apo4.cab /path/to/GenericNahimicRestoreTool.exe runtime --hardware msi-gf63-11ucx
```

The MSI OEM source is `Drivers\\EXT\\MSI\\APO4\\NH3ProductSettings0.cab`. Its speaker XML declares `SUBSYS_1462134C`, `InternalSpeakers`, and device UUID `{c7e78668-755a-4baa-9f3c-3f2c64d60e9d}`. The verified profile SHA-256 is `d7217235268c80b6b2573acbf27f1d55aad4281c114b455e7aa9cad77ebec1a6`.

## Local installation

See [docs/FEDORA-MSI.md](docs/FEDORA-MSI.md) for the local installer, activation, rollback, and publication checklist. The existing upstream AUR recipe remains upstream-oriented; it is not a prebuilt Fedora package of this adaptation.

Do not run two copies of the speaker filter, or stack the previous EQ trial over Nahimic. Start listening at modest speaker volume and increase gradually; stop if there is distortion or speaker rattling.

## Changes from upstream

- Strict MSI codec/subsystem mapping and OEM XML validation.
- Explicit device filename passed into the C++ host rather than a hardcoded MECHREVO path.
- Precise Wine wall-clock reads to prevent valid Linux volume state being rejected as future-dated; freshness checks are retained.
- Portable GUI/runtime/service configuration and opt-in local installation.
- MSI extraction and checksum-verified official downloads; no redistributed DSP binaries.
- Regression tests for hardware gates, configuration, and local GUI paths.

Original documentation: [English](README.en.md). Contributions should include exact hardware IDs and actual test evidence; passing unit tests alone is not proof of support for a new laptop.
