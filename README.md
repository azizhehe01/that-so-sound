# Nahimic Linux — MSI/Fedora Adaptation 🎧🔥

Proyek adaptasi sumber terbuka dari [wearzdk/nahimic-linux](https://github.com/wearzdk/nahimic-linux) (basis commit `6d8a826` / v0.3.0). Di fork ini, gua nambahin dukungan speaker buat **MSI GF63 Thin 11UCX** plus jalur instalasi lokal yang praktis.

> ⚠️ **Disclaimer Santai tapi Penting**: Ini bukan rilis resmi dari Nahimic, MSI, SteelSeries, ataupun Fedora. Segala risiko speaker jebol karena lu maksa config ngawur ditanggung sendiri ya bre!

---

## 🧐 Apaan nih Proyekan?

Singkatnya: speaker laptop di Linux itu sering banget suaranya cempreng, tipis, dan nggak ada nendang-nendangnya karena DSP tuning bawaan pabrik cuma aktif di Windows.

Nah, aplikasi ini nge-bridge runtime resmi **Nahimic APO4 (driver Windows asli)** ke audio server Linux (**PipeWire**) lewat bantuan Wine. Jadi kita **nggak bikin ulang DSP-nya dari nol**, tapi ngebungkus DLL aslinya biar bisa jalan di Linux. 

Panel GUI-nya pake Qt/PySide6, lengkap dengan:
- Profil audio (Music, Movie, Gaming, Communication)
- Bass Boost & Treble
- Voice Clarity
- Virtual Surround Sound
- Volume Stabilization (biar ga kaget pas volume mendadak naik)
- 10-Band Equalizer

---

## 💻 Laptop yang Bisa Pake (Hardware Limits)

Gua ingetin dari awal: **jangan asal install kalau laptop lo beda!**

Saat ini yang udah di-whitelist dan diverifikasi:
1. **MSI GF63 Thin 11UCX / MS-16R6**
   - Codec: Realtek ALC897 (`10ec0897`, subsystem `1462134c`).
   - Profil: Wajib pake config OEM resmi `1462134C_InternalSpeakers.nsx`.
2. **MECHREVO Wujie 14X Pro (Upstream Bawaan)**
   - Codec: Senary (`14f11f87`, subsystem `1d05e022`).

> 🚫 **Hardware lain bakal otomatis di-reject!** 
> Jangan ganti-ganti nama file settingan laptop lain buat ngebypass validasi ya bre. Profil akustik speaker tiap laptop itu beda-beda. Kalau dipaksa, suaranya bisa distorsi parah (*rattling*) atau bahkan ngerusak membran speaker fisik lo!

---

## 🛠️ Persiapan & Dependencies (Khusus Fedora)

Pastikan sistem lo pake Linux 64-bit (x86_64), PipeWire Pulse, WirePlumber 0.5+, dan ada systemd user session.

Install dulu dependensi build-nya:

```sh
sudo dnf install wine mingw64-gcc-c++ python3-pyside6 pulseaudio-libs-devel gcc make pkgconf-pkg-config cabextract
```

Terus build host C++ dan jalanin unit test:

```sh
make -j4
python3 -m unittest discover -s tests -v
```

---

## 📦 Runtime & Komponen Vendor (Ga Dibundel di Sini)

Karena alasan lisensi dan hak cipta, repo ini **nggak nyimpen** file `.exe`, `.dll`, `.cab`, atau `.nsx` bajakan. Kode komunitas kita lisensinya MIT, tapi runtime Nahimic tetep milik vendor aslinya.

Lo bisa download arsip resmi dan verifikasi checksum SHA-256 otomatis lewat skrip:

```sh
python3 scripts/fetch-runtime.py --hardware msi-gf63-11ucx --output runtime
```

Atau kalau lo udah punya file installer/CAB Nahimic Windows-nya di lokal, tinggal ekstrak manual:

```sh
python3 packaging/extract_runtime.py /path/to/nahimic-apo4.cab /path/to/GenericNahimicRestoreTool.exe runtime --hardware msi-gf63-11ucx
```

*(Sumber OEM MSI asalnya dari `Drivers\EXT\MSI\APO4\NH3ProductSettings0.cab` dengan profil `1462134C_InternalSpeakers.nsx` dan SHA-256 terverifikasi: `d7217235268c80b6b2573acbf27f1d55aad4281c114b455e7aa9cad77ebec1a6`).*

---

## 🚀 Instalasi & Cara Pake

Cek panduan lengkapnya di [docs/FEDORA-MSI.md](docs/FEDORA-MSI.md) buat aktivasi service lokal dan rollback.

Kalo service udah jalan, cek statusnya lewat terminal:

```sh
nahimic --status
systemctl --user status nahimic.service
journalctl --user -u nahimic.service -b
```

Buka panel GUI-nya lewat menu aplikasi atau ketik:
```sh
nahimic
```

> 💡 **Tips dari gua**: Pas pertama kali nyetel setelah install, setel volume pelan-pelan dulu dari kecil. Dengerin baik-baik, kalo ada suara sember atau speaker getar aneh, langsung matiin!

---

## 🔄 Apa Aja yang Diubah dari Upstream?

- **Validasi Hardware Ketat**: Cek codec/subsystem ID MSI dan validasi XML OEM biar ga salah pasang.
- **Dynamic Device Filename**: C++ host nerima nama file profil dinamis, ga di-hardcode ke MECHREVO lagi.
- **Perbaikan Clock Wine**: Pembacaan wall-clock Wine dibikin lebih presisi biar volume state Linux ga dikira "future-dated".
- **Skrip Ekstraksi MSI**: Tool download dan ekstraksi checksum resmi khusus profil MSI.
- **Suite Test Lengkap**: Ditambahin unit tests buat hardware gate, path portabel, dan GUI lokal.

---

## 🤝 Lisensi

- Kode komunitas & host: [MIT License](LICENSE).
- Binary runtime & profil OEM Nahimic: Hak cipta milik vendor / [Notice](packaging/LicenseRef-Nahimic).

