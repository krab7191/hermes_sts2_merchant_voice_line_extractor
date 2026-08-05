# Slay the Spire 2 — Merchant Voice Line Extractor & Soundboard

> Extract the Merchant's voice lines from *Slay the Spire 2* game files and play them on a cosplay soundboard.

This project provides a Python script for pulling the Merchant's voice clips out of the game's FMOD sound banks (bundled inside the Godot `.pck` archive) and a self-contained HTML soundboard app for triggering those clips at conventions, photo ops, or wherever your Merchant cosplay takes you.

The Merchant speaks a fictional mumbling language — 12 voice lines confirmed by Mega Crit Games — so the soundboard plays random clips to capture the vibe without needing to match specific phrases to situations.

---

## Table of Contents

- [What's Included](#whats-included)
- [Prerequisites](#prerequisites)
- [Setup & Extraction](#setup--extraction)
  - [Step 1 — Install GDRE Tools](#step-1--install-gdre-tools)
  - [Step 2 — Install vgmstream](#step-2--install-vgmstream)
  - [Step 3 — Extract the `.pck` archive](#step-3--extract-the-pck-archive)
  - [Step 4 — Run the extraction script](#step-4--run-the-extraction-script)
  - [Step 5 — Convert to MP3 (optional but recommended)](#step-5--convert-to-mp3-optional-but-recommended)
- [Soundboard Setup](#soundboard-setup)
- [Using the Soundboard at a Convention](#using-the-soundboard-at-a-convention)
- [Project Structure](#project-structure)
- [Legal / Fair Use Notice](#legal--fair-use-notice)
- [Credits](#credits)

---

## What's Included

| File | Description |
|---|---|
| `extract_merchant_voices.py` | Python script that scans extracted game files for the FMOD `sfx.bank`, identifies Merchant voice lines, and extracts/converts them to individual audio files. |
| `merchant_soundboard.html` | A single-file HTML/CSS/JS web app that auto-detects MP3 files in the `sounds/` directory and lets you play them individually or at random. Designed for mobile use at conventions. |

---

## Prerequisites

| Tool | Purpose | Link |
|---|---|---|
| **Python 3.8+** | Runs the extraction script | [python.org](https://www.python.org/downloads/) |
| **GDRE Tools** | Decompresses the Godot `.pck` archive to access the FMOD sound banks inside | [github.com/bruvzg/gdsdecomp](https://github.com/bruvzg/gdsdecomp) |
| **vgmstream** | Decodes FMOD `.fsb` / `.bank` audio streams into WAV | [github.com/vgmstream/vgmstream](https://github.com/vgmstream/vgmstream) |
| **ffmpeg** *(optional)* | Converts extracted WAV files to MP3 for smaller file sizes and better browser compatibility | [ffmpeg.org](https://ffmpeg.org/download.html) |

You also need a legitimate copy of **Slay the Spire 2** on Steam.

---

## Setup & Extraction

### Step 1 — Install GDRE Tools

Download the latest release from the [GDRE Tools releases page](https://github.com/bruvzg/gdsdecomp/releases). It's a standalone executable — no installation required. Just extract the archive and note the path to `gdre_tools`.

### Step 2 — Install vgmstream

Download the latest build from the [vgmstream releases page](https://github.com/vgmstream/vgmstream/releases). You'll need:

- `vgmstream-cli` (the command-line decoder, sometimes called `test.exe` or `vgmstream`)

Add it to your `PATH` or note its full path — the extraction script calls it via subprocess.

### Step 3 — Extract the `.pck` archive

Locate your Slay the Spire 2 installation. On Steam the default path is:

```
Steam/steamapps/common/Slay the Spire 2/
```

Look for a `.pck` file (typically named something like `game.pck` or the project name). Open GDRE Tools and:

1. **File → Recover Project** (or "PCK Explorer")
2. Select the `.pck` file from your StS2 install directory
3. Choose an output directory — use `extraction/` inside this repo:
   ```
   /path/to/hermes_sts2_merchant_voice_line_extractor/extraction/
   ```
4. Click **Recover** and wait for the process to finish

The extracted files will include the FMOD sound banks (look for `sfx.bank` or similar `.bank` / `.fsb` files).

### Step 4 — Run the extraction script

```bash
cd /path/to/hermes_sts2_merchant_voice_line_extractor

python3 extract_merchant_voices.py \
    --extraction-dir ./extraction \
    --output-dir ./merchant_voices \
    --vgmstream-path /path/to/vgmstream-cli
```

The script will:

1. Scan `extraction/` recursively for FMOD sound bank files
2. Identify the Merchant's voice lines from `sfx.bank`
3. Use vgmstream to decode each clip to WAV
4. Save individual files to `merchant_voices/`

You should see output like:

```
Found sfx.bank: extraction/path/to/sfx.bank
Decoded 12 merchant voice lines → merchant_voices/
  merchant_01.wav
  merchant_02.wav
  ...
  merchant_12.wav
```

Run `python3 extract_merchant_voices.py --help` to see all available options.

### Step 5 — Convert to MP3 (optional but recommended)

The soundboard works best with MP3 files (smaller size, universal browser support). If you have ffmpeg installed, convert the WAVs:

```bash
cd merchant_voices
for f in merchant_*.wav; do
    ffmpeg -i "$f" -codec:a libmp3lame -qscale:a 2 "../sounds/${f%.wav}.mp3"
done
```

Or use the script's built-in conversion if ffmpeg is on your `PATH`:

```bash
python3 extract_merchant_voices.py \
    --extraction-dir ./extraction \
    --output-dir ./merchant_voices \
    --sounds-dir ./sounds \
    --convert-mp3
```

This will place `merchant_01.mp3` through `merchant_12.mp3` directly in `sounds/`.

---

## Soundboard Setup

1. Place your MP3 files in the `sounds/` directory:
   ```
   sounds/
   ├── merchant_01.mp3
   ├── merchant_02.mp3
   ├── ...
   └── merchant_12.mp3
   ```

2. Open `merchant_soundboard.html` in any modern browser (Chrome, Firefox, Safari, Edge). You can simply double-click the file.

3. The soundboard will auto-detect all `merchant_*.mp3` files in the `sounds/` directory and display a button for each.

> **Note:** Because the soundboard loads local audio files via JavaScript, some browsers may require you to serve it through a local web server. If buttons appear but no sound plays, run:
>
> ```bash
> cd /path/to/hermes_sts2_merchant_voice_line_extractor
> python3 -m http.server 8000
> ```
>
> Then open `http://localhost:8000/merchant_soundboard.html` in your browser.

---

## Using the Soundboard at a Convention

The soundboard is designed with cosplay in mind — big buttons, random playback, and no internet required.

### On your phone (recommended)

1. Transfer the `sounds/` folder and `merchant_soundboard.html` to your phone.
2. Open the HTML file in your mobile browser.
3. **Pro tip:** For reliable audio on iOS, the first tap serves as the user-gesture unlock — tap any button once before you need it for real.
4. Use the **🎲 Random** button to play a random Merchant voice line.
5. Tap individual buttons to play specific clips.
6. Keep your phone in a pocket or prop with just the screen accessible for tapping.

### Tips for convention use

- **Battery:** Turn down screen brightness and close background apps. The soundboard is lightweight but you'll want juice for the whole day.
- **Volume:** Pair your phone with a small Bluetooth speaker tucked into your costume for volume that cuts through convention noise. A clip-on or hidden speaker works great.
- **Offline:** The soundboard is 100% offline — no Wi-Fi or cellular needed. Perfect for crowded convention halls with spotty signal.
- **Practice:** Get familiar with which button plays which clip so you can trigger the right mood (greeting, haggling, dramatic, etc.) even though it's gibberish.
- **Permissions:** If your phone auto-locks, adjust your screen timeout to a longer interval so you don't have to unlock mid-interaction.

---

## Project Structure

```
hermes_sts2_merchant_voice_line_extractor/
├── README.md                          # This file
├── .gitignore                         # Ignores extracted audio, output dirs, etc.
├── extract_merchant_voices.py         # Python extraction script
├── merchant_soundboard.html           # Self-contained soundboard web app
├── sounds/                            # Place final MP3 files here (gitignored)
│   └── .gitkeep                       # Keeps the directory in git
├── extraction/                        # GDRE Tools output (gitignored)
└── merchant_voices/                   # Extraction script output (gitignored)
```

> **Note:** Audio files (`sounds/*.mp3`, `sounds/*.wav`, `sounds/*.ogg`) and extraction outputs (`extraction/`, `merchant_voices/`) are listed in `.gitignore` and will **not** be committed to the repository. This is intentional — the audio is copyrighted and should not be redistributed. Each user extracts their own files from their own legally-owned copy of the game.

---

## Legal / Fair Use Notice

This project is a **fan-made, non-commercial** tool created for personal cosplay use. It does not distribute any copyrighted audio assets.

- **Slay the Spire 2** and all its audio content are © Mega Crit Games. All rights belong to them.
- The extraction tools (GDRE Tools, vgmstream) are open-source projects unaffiliated with Mega Crit Games or this project.
- This project provides **only the extraction script and soundboard code** — no game audio is included in the repository.
- Users must own a legitimate copy of Slay the Spire 2 to extract audio from it.
- The extracted audio files are for **personal use only** (e.g., your own cosplay). Do not upload, share, or redistribute the extracted audio files publicly.
- The soundboard code itself (HTML/CSS/JS) and the Python extraction script are provided under the MIT License (see `LICENSE` if applicable).

If you are a rights holder and have concerns, please open an issue.

---

## Credits

This project stands on the shoulders of the Slay the Spire modding/research community:

- **[GDRE Tools](https://github.com/bruvzg/gdsdecomp)** by bruvzg — Godot project recovery and `.pck` decompression tool, essential for accessing the game's internal file structure.
- **[vgmstream](https://github.com/vgmstream/vgmstream)** — Open-source decoder for FMOD and other game audio formats, used to convert the sound bank audio into playable WAV files.
- **[spire-codex](https://github.com/alexdriedger/spire-codex)** by alexdriedger — Slay the Spire data extraction methodology that inspired the approach to parsing game files.
- **[sts2-ancients-peon](https://github.com/funny-nation/sts2-ancients-peon)** by funny-nation — Slay the Spire 2 research project whose work on FMOD sound bank identification informed the extraction workflow.
- **Mega Crit Games** — For making an incredible game and a delightfully incomprehensible Merchant.

---

*This is an unofficial fan project. Slay the Spire 2 is a trademark of Mega Crit Games. This project is not affiliated with or endorsed by Mega Crit Games.*