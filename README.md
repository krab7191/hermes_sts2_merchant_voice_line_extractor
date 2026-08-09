# Slay the Spire 2 — Merchant Voice Line Extractor

> Extract the Merchant's voice lines from *Slay the Spire 2* game files.

This project is a Python script for pulling the Merchant's voice clips out of the game's FMOD sound bank (bundled inside the Godot `.pck` archive) — decoding, converting, and organizing them for downstream use (cosplay soundboards, fan projects, whatever you're building).

The Merchant speaks a fictional mumbling language. As of the current game version there are **27 distinct Merchant clips** in the sound bank: 14 forward-playing lines across 5 emotional categories (`welcome`, `thank_yous`, `dissapointment`, `passive`, `laughter`), plus 13 backwards/reversed clips across 3 categories (`die`, `hehe`, `hurt_sad`) used for specific in-game moments. All of this was confirmed directly from the game's own FMOD sound bank — see [How the naming works](#how-the-naming-works) below.

> **Looking for the soundboard?** The HTML/JS soundboard that used to live in this repo has moved to a proper web app: [`sts2_merchant_audio_board`](../sts2_merchant_audio_board), an Astro + Svelte site with per-category buttons. This repo now focuses purely on extraction.

---

## Table of Contents

- [What's Included](#whats-included)
- [Prerequisites](#prerequisites)
- [Setup & Extraction](#setup--extraction)
  - [Step 1 — Install GDRE Tools](#step-1--install-gdre-tools)
  - [Step 2 — Install vgmstream](#step-2--install-vgmstream)
  - [Step 3 — Run the extraction script](#step-3--run-the-extraction-script)
- [How the naming works](#how-the-naming-works)
- [Project Structure](#project-structure)
- [Legal / Fair Use Notice](#legal--fair-use-notice)
- [Credits](#credits)

---

## What's Included

| File | Description |
|---|---|
| `extract_merchant_voices.py` | Python script that locates your Slay the Spire 2 install, pulls just the FMOD sound banks out of the `.pck`, identifies Merchant voice lines in `sfx.bank`, decodes them, converts them to MP3, and drops sequentially-numbered files into `sounds/` and descriptively-named ones into `merchant_voices/`. |

---

## Prerequisites

| Tool | Purpose | Link |
|---|---|---|
| **Python 3.8+** | Runs the extraction script | [python.org](https://www.python.org/downloads/) |
| **GDRE Tools** | Extracts the FMOD sound banks out of the Godot `.pck` archive | [github.com/GDRETools/gdsdecomp](https://github.com/GDRETools/gdsdecomp/releases) |
| **vgmstream-cli** | Decodes the FMOD bank's audio streams into WAV | [github.com/vgmstream/vgmstream](https://github.com/vgmstream/vgmstream/releases) |
| **ffmpeg** *(optional)* | Converts extracted WAV files to MP3 for smaller file sizes and better browser compatibility | [ffmpeg.org](https://ffmpeg.org/download.html) |

You also need a legitimate copy of **Slay the Spire 2** on Steam.

> **Running under WSL?** GDRE Tools' native Linux build requires a newer glibc (≥ 2.35) than some WSL distros ship (e.g. Ubuntu 20.04 has 2.31). If `gdre_tools` fails to launch with `GLIBC_2.3x not found` errors, download the **Windows** build of GDRE Tools instead — WSL can run `.exe` files directly via its interop layer. The script detects when the GDRE binary is a `.exe` and automatically converts POSIX paths to Windows paths for it via `wslpath`. vgmstream-cli's native Linux build works fine as-is under WSL; no special handling needed there.

---

## Setup & Extraction

### Step 1 — Install GDRE Tools

Download the latest release from the [GDRE Tools releases page](https://github.com/GDRETools/gdsdecomp/releases) (`GDRE_tools-vX.Y.Z-linux.zip`, `-windows.zip`, or `-macos.zip`). It's a standalone executable — no installation required, just unzip it. Make it executable (`chmod +x gdre_tools.x86_64` on Linux/macOS) and either put it on your `PATH` as `gdre_tools` or note its path for `--gdre-path`.

### Step 2 — Install vgmstream

Download the latest build from the [vgmstream releases page](https://github.com/vgmstream/vgmstream/releases) — you need `vgmstream-cli` (Linux/macOS builds ship it as a plain binary named `vgmstream-cli`; Windows builds call it `vgmstream-cli.exe`). `chmod +x` it if needed, then put it on your `PATH` or note its path for `--vgmstream-path`.

### Step 3 — Run the extraction script

That's it for manual steps — the script does everything else itself: finds your Steam install, locates the `.pck`, pulls just the FMOD bank files out of it (not a full project decompile — that would be slow and unnecessary), decodes the Merchant's lines, converts them to MP3, and copies soundboard-ready files into `sounds/`.

```bash
cd /path/to/hermes_sts2_merchant_voice_line_extractor
python3 extract_merchant_voices.py
```

If auto-detection can't find your Steam library or the tools aren't on `PATH`, point at them explicitly:

```bash
python3 extract_merchant_voices.py \
    --game-path "/path/to/Steam/steamapps/common/Slay the Spire 2" \
    --gdre-path /path/to/gdre_tools \
    --vgmstream-path /path/to/vgmstream-cli
```

Expected output looks like:

```
━━━ Extraction Summary

  Total subsongs in sfx.bank : 1929
  Merchant voice lines found : 27
  Successfully decoded (.wav): 27
  Converted to .mp3          : 27

  Output directory: /path/to/merchant_voices
  Sounds directory: /path/to/sounds  (27 files)

[OK] Done! Your merchant voice files are ready to use.
[OK] 27 soundboard-ready file(s) copied to /path/to/sounds.
```

Useful flags (`python3 extract_merchant_voices.py --help` for the full list):

| Flag | Default | Purpose |
|---|---|---|
| `--output-dir` | `merchant_voices` | Where descriptively-named files (e.g. `sts2_sfx_VO_merchant_welcome_v1_rr1.mp3`) are kept, for reference. |
| `--sounds-dir` | `sounds` | Where sequentially-numbered, soundboard-ready files (`merchant_01.mp3`, `merchant_02.mp3`, ...) are copied. Set to `""` to skip this. |
| `--exclude-reverse-lines` | off | Only extract the 5 forward-playing categories; skip the 3 backwards `reverse_merchant_*` clips. |
| `--keep-wav` | off | Keep the intermediate `.wav` files instead of deleting them once converted to `.mp3`. |
| `--skip-extraction` | off | Skip the GDRE `.pck` extraction step and reuse an existing `--extraction-dir` (fast iteration once you've already pulled the bank files once). |

---

## How the naming works

The Merchant's clips live in `res://banks/desktop/sfx.bank`, one of several FMOD banks in the `.pck` (the others hold music and ambience, not voice lines). Inside `sfx.bank`, each of the 1929 subsongs has an internal name like:

```
sts2_sfx_VO_merchant_welcome_v1_rr1
sts2_sfx_VO_reverse_merchant_hehe_v1_rr3
```

`VO` = voice-over, `merchant` = the character, `welcome`/`hehe`/etc. = the emotional category, `v1` = variant, `rr1`..`rrN` = "round robin" takes (the game randomly cycles through these to avoid repeating the exact same take back-to-back — the soundboard does the same). The `reverse_merchant_*` clips are genuinely backwards-played takes shipped by Mega Crit for specific moments (not a script bug) — they're included by default since they're real Merchant assets; pass `--exclude-reverse-lines` if you'd rather leave them out.

---

## Project Structure

```
hermes_sts2_merchant_voice_line_extractor/
├── README.md                          # This file
├── .gitignore                         # Ignores extracted audio, output dirs, etc.
├── extract_merchant_voices.py         # Python extraction script
├── sounds/                            # Sequentially-numbered merchant_NN.mp3 files (gitignored)
│   └── .gitkeep                       # Keeps the directory in git
├── sts2_extraction/                   # GDRE Tools output — raw .bank files (gitignored)
└── merchant_voices/                   # Descriptively-named decoded files, for reference (gitignored)
```

> **Note:** Audio files (`sounds/*.mp3`, `sounds/*.wav`, `sounds/*.ogg`) and extraction outputs (`sts2_extraction/`, `merchant_voices/`) are listed in `.gitignore` and will **not** be committed to the repository. This is intentional — the audio is copyrighted and should not be redistributed. Each user extracts their own files from their own legally-owned copy of the game.

---

## Legal / Fair Use Notice

This project is a **fan-made, non-commercial** tool. It does not distribute any copyrighted audio assets.

- **Slay the Spire 2** and all its audio content are © Mega Crit Games. All rights belong to them.
- The extraction tools (GDRE Tools, vgmstream) are open-source projects unaffiliated with Mega Crit Games or this project.
- This project provides **only the extraction script** — no game audio is included in the repository.
- Users must own a legitimate copy of Slay the Spire 2 to extract audio from it.
- The Python extraction script itself is provided under the MIT License (see `LICENSE` if applicable). What you do with the audio you extract (and how you distribute it downstream) is your own call to make.

If you are a rights holder and have concerns, please open an issue.

---

## Credits

This project stands on the shoulders of the Slay the Spire modding/research community:

- **[GDRE Tools](https://github.com/GDRETools/gdsdecomp)** — Godot project recovery and `.pck` extraction tool, essential for accessing the game's internal file structure.
- **[vgmstream](https://github.com/vgmstream/vgmstream)** — Open-source decoder for FMOD and other game audio formats, used to convert the sound bank audio into playable WAV files.
- **Mega Crit Games** — For making an incredible game and a delightfully incomprehensible Merchant.

---

*This is an unofficial fan project. Slay the Spire 2 is a trademark of Mega Crit Games. This project is not affiliated with or endorsed by Mega Crit Games.*
