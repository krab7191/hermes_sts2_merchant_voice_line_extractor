#!/usr/bin/env python3
"""
Slay the Spire 2 — Merchant Voice Extractor
============================================

This script extracts the merchant's voice lines from Slay the Spire 2's game
files so they can be used in a soundboard / cosplay project.

It is designed to be run by someone who OWNS the game on Steam. It does NOT
download anything illegal — it reads files you already have on your own machine.

PREREQUISITES (install these first):
------------------------------------
1. **GDRE Tools** — used to extract the Godot .pck file.
   Download from: https://github.com/bruvzg/gdsdecomp/releases
   After installing, make sure `gdre_tools` is on your PATH, or pass
   its location with --gdre-path.

2. **vgmstream-cli** — used to decode FMOD sound banks into .wav.
   Download from: https://github.com/vgmstream/vgmstream/releases
   After installing, make sure `vgmstream-cli` is on your PATH, or pass
   its location with --vgmstream-path.

3. **ffmpeg** (optional) — if installed, the script also converts .wav → .mp3.
   Download from: https://ffmpeg.org/download.html

USAGE:
------
    # Fully automatic — auto-detects Steam, StS2, and tools on PATH:
    python extract_merchant_voices.py

    # Specify everything manually:
    python extract_merchant_voices.py \\
        --game-path "C:\\Program Files (x86)\\Steam\\steamapps\\common\\Slay the Spire 2" \\
        --gdre-path "C:\\Tools\\gdre_tools.exe" \\
        --vgmstream-path "C:\\Tools\\vgmstream-cli.exe"

    # Also set a custom output directory:
    python extract_merchant_voices.py --output-dir ./my_voices

WHAT THE SCRIPT DOES (step by step):
-------------------------------------
  1. Finds the Steam install directory (Windows / Linux / macOS).
  2. Locates "Slay the Spire 2.pck" inside the game folder.
  3. Uses GDRE Tools to extract the .pck into a temporary extraction directory.
  4. Finds "sfx.bank" inside the extracted files (FMOD sound bank).
  5. Lists all subsongs in sfx.bank using vgmstream-cli.
  6. Filters subsongs whose names contain "merchant".
  7. Decodes each merchant subsong to .wav using vgmstream-cli.
  8. If ffmpeg is available, converts each .wav to .mp3.
  9. Saves everything to the output directory (default: merchant_voices/).
 10. Prints a clear summary of what was extracted.

Author: Generated for StS2 Merchant Cosplay project
"""

from __future__ import annotations

import argparse
import os
import platform
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import List, Optional, Tuple


# ---------------------------------------------------------------------------
# Pretty printing helpers
# ---------------------------------------------------------------------------

class Colors:
    """ANSI colour codes for nicer terminal output. Auto-disabled on Windows
    if colour support is unavailable."""
    HEADER = "\033[95m"
    BLUE = "\033[94m"
    CYAN = "\033[96m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    BOLD = "\033[1m"
    RESET = "\033[0m"


def _supports_color() -> bool:
    """Check if the terminal likely supports ANSI colours."""
    if platform.system() == "Windows":
        # Windows 10+ supports ANSI; older versions may not.
        return sys.stdout.isatty()
    return hasattr(sys.stdout, "isatty") and sys.stdout.isatty()


_USE_COLOR = _supports_color()


def _c(text: str, color: str) -> str:
    """Wrap text in ANSI colour codes if colour is supported."""
    if _USE_COLOR:
        return f"{color}{text}{Colors.RESET}"
    return text


def info(msg: str) -> None:
    """Print an informational message."""
    print(f"{_c('[INFO]', Colors.CYAN)} {msg}")


def step(msg: str) -> None:
    """Print a step header — used for major pipeline stages."""
    print(f"\n{_c('━━━ ', Colors.BLUE)}{_c(msg, Colors.BOLD)}")


def success(msg: str) -> None:
    """Print a success message."""
    print(f"{_c('[OK]', Colors.GREEN)} {msg}")


def warn(msg: str) -> None:
    """Print a warning message."""
    print(f"{_c('[WARN]', Colors.YELLOW)} {msg}")


def error(msg: str) -> None:
    """Print an error message."""
    print(f"{_c('[ERROR]', Colors.RED)} {msg}", file=sys.stderr)


def banner() -> None:
    """Print a nice banner at script start."""
    title = "Slay the Spire 2 — Merchant Voice Extractor"
    line = "═" * (len(title) + 4)
    print()
    print(_c(f"╔{line}╗", Colors.HEADER))
    print(_c(f"║  {title}  ║", Colors.HEADER))
    print(_c(f"╚{line}╝", Colors.HEADER))
    print()


# ---------------------------------------------------------------------------
# Step 1: Find the Steam install directory
# ---------------------------------------------------------------------------

# Common Steam library paths on each OS. We'll check all of these.
# The game lives under <steam_library>/steamapps/common/Slay the Spire 2

def get_candidate_steam_paths() -> List[Path]:
    """
    Return a list of candidate Steam library paths for the current OS.

    Steam libraries are the directories that contain a `steamapps` folder.
    The game itself lives under `<steam_library>/steamapps/common/Slay the Spire 2`.

    We check the default install location as well as common alternate locations
    (e.g. when users have Steam on a different drive).
    """
    system = platform.system()
    candidates: List[Path] = []

    if system == "Windows":
        # Default Windows install locations
        candidates.extend([
            Path("C:/Program Files (x86)/Steam"),
            Path("C:/Program Files/Steam"),
            # Common alternate-drive patterns (D:, E:, etc.)
            Path("D:/Steam"),
            Path("E:/Steam"),
            Path("D:/SteamLibrary"),
            Path("E:/SteamLibrary"),
            Path("C:/SteamLibrary"),
        ])
        # Also check the environment variable STEAM_PATH if set
        steam_env = os.environ.get("STEAM_PATH")
        if steam_env:
            candidates.append(Path(steam_env))

    elif system == "Linux":
        # Default Linux install location
        candidates.append(Path.home() / ".local/share/Steam")
        # Flatpak Steam
        candidates.append(Path.home() / ".var/app/com.valvesoftware.Steam/data/Steam")
        # Steam on a secondary drive (common pattern)
        # We'll also check common mount points
        for drive in ["D", "E", "F"]:
            candidates.append(Path(f"/mnt/{drive.lower()}/Steam"))
            candidates.append(Path(f"/media/{drive.lower()}/Steam"))

    elif system == "Darwin":  # macOS
        candidates.append(Path.home() / "Library/Application Support/Steam")

    else:
        # Unknown OS — try the Linux path as a fallback
        warn(f"Unknown OS '{system}', trying Linux-style Steam paths.")
        candidates.append(Path.home() / ".local/share/Steam")

    # De-duplicate while preserving order
    seen = set()
    unique: List[Path] = []
    for c in candidates:
        resolved = c.resolve() if c.exists() else c
        if resolved not in seen:
            seen.add(resolved)
            unique.append(c)
    return unique


def find_library_folders(steam_path: Path) -> List[Path]:
    """
    Parse Steam's `libraryfolders.vdf` to find additional Steam library folders.

    Steam stores info about all library folders (including those on other drives)
    in `<steam_path>/steamapps/libraryfolders.vdf`. This file is in Valve's VDF
    format, which is similar to JSON but not exactly JSON. We use a simple regex
    to extract quoted path strings.

    Returns a list of Path objects, always including the steam_path itself
    (since the default library is there).
    """
    vdf_path = steam_path / "steamapps" / "libraryfolders.vdf"
    libraries: List[Path] = [steam_path]

    if not vdf_path.exists():
        return libraries

    try:
        content = vdf_path.read_text(encoding="utf-8", errors="replace")
    except Exception as e:
        warn(f"Could not read {vdf_path}: {e}")
        return libraries

    # In libraryfolders.vdf, each library entry has a "path" key like:
    #     "path"        "D:\\Games\\Steam"
    # We extract all "path" values with a regex.
    path_pattern = re.compile(r'"path"\s+"([^"]+)"')
    matches = path_pattern.findall(content)

    for m in matches:
        # VDF paths on Windows use double backslashes; normalize them
        clean = m.replace("\\\\", "\\")
        lib_path = Path(clean)
        if lib_path.exists() and lib_path not in libraries:
            libraries.append(lib_path)

    return libraries


def find_sts2_install(explicit_path: Optional[str] = None) -> Optional[Path]:
    """
    Find the Slay the Spire 2 install directory.

    If `explicit_path` is provided, use it directly (after checking it exists).
    Otherwise, search all known Steam library locations for:
        <library>/steamapps/common/Slay the Spire 2

    Returns the Path to the game directory, or None if not found.
    """
    game_folder_name = "Slay the Spire 2"

    # --- If the user gave us an explicit path, just use it ---
    if explicit_path:
        game_path = Path(explicit_path)
        if game_path.exists() and game_path.is_dir():
            success(f"Using user-specified game path: {game_path}")
            return game_path
        else:
            error(f"The path you specified does not exist or is not a directory: {game_path}")
            return None

    # --- Auto-detect: search all candidate Steam library locations ---
    info("Searching for your Steam installation...")

    steam_paths = get_candidate_steam_paths()
    all_libraries: List[Path] = []

    for sp in steam_paths:
        if sp.exists():
            info(f"  Found Steam directory: {sp}")
            # Also find any additional library folders configured in this Steam install
            libs = find_library_folders(sp)
            all_libraries.extend(libs)

    if not all_libraries:
        error("Could not find a Steam installation on this system.")
        error("Please specify the game path manually with --game-path, e.g.:")
        error('  python extract_merchant_voices.py --game-path "C:\\Program Files (x86)\\Steam\\steamapps\\common\\Slay the Spire 2"')
        return None

    # Search each library for the game
    for lib in all_libraries:
        game_path = lib / "steamapps" / "common" / game_folder_name
        if game_path.exists() and game_path.is_dir():
            success(f"Found Slay the Spire 2 at: {game_path}")
            return game_path

    # Not found — print helpful message
    error("Slay the Spire 2 was not found in any detected Steam library.")
    error("Checked the following libraries:")
    for lib in all_libraries:
        error(f"  - {lib / 'steamapps' / 'common' / game_folder_name}")
    error("")
    error("Please specify the game path manually with --game-path.")
    return None


# ---------------------------------------------------------------------------
# Step 2: Find the .pck file
# ---------------------------------------------------------------------------

def find_pck_file(game_path: Path) -> Optional[Path]:
    """
    Find 'Slay the Spire 2.pck' in the game directory.

    The .pck file is Godot's packed resource archive. For StS2 it sits at
    the root of the game install directory.
    """
    # Primary expected location
    pck_path = game_path / "Slay the Spire 2.pck"
    if pck_path.exists():
        size_mb = pck_path.stat().st_size / (1024 * 1024)
        success(f"Found .pck file: {pck_path} ({size_mb:.1f} MB)")
        return pck_path

    # Fallback: search for any .pck file in the game directory
    pck_files = list(game_path.glob("*.pck"))
    if pck_files:
        # Pick the largest one — the main game .pck is typically the biggest
        pck_files.sort(key=lambda p: p.stat().st_size, reverse=True)
        pck_path = pck_files[0]
        size_mb = pck_path.stat().st_size / (1024 * 1024)
        warn(f"Did not find 'Slay the Spire 2.pck' by exact name.")
        warn(f"Using the largest .pck file instead: {pck_path.name} ({size_mb:.1f} MB)")
        return pck_path

    error(f"No .pck file found in: {game_path}")
    error("Make sure Slay the Spire 2 is fully installed (not just downloaded).")
    return None


# ---------------------------------------------------------------------------
# Step 3: Locate external tools (GDRE Tools, vgmstream, ffmpeg)
# ---------------------------------------------------------------------------

def find_tool(name: str, explicit_path: Optional[str] = None) -> Optional[str]:
    """
    Find an external command-line tool.

    If `explicit_path` is given, verify it exists and return it.
    Otherwise, search the system PATH using shutil.which().

    Returns the full path to the tool, or None if not found.
    """
    if explicit_path:
        # User specified a path — check it exists
        p = Path(explicit_path)
        if p.exists():
            return str(p)
        else:
            error(f"Tool not found at specified path: {explicit_path}")
            return None

    # Search on PATH
    # On Windows, also try with .exe extension
    found = shutil.which(name)
    if found:
        return found

    # Windows fallback: try with .exe
    if platform.system() == "Windows":
        found = shutil.which(name + ".exe")
        if found:
            return found

    return None


# ---------------------------------------------------------------------------
# Step 4: Extract the .pck file using GDRE Tools
# ---------------------------------------------------------------------------

def extract_pck(gdre_path: str, pck_path: Path, output_dir: Path) -> bool:
    """
    Extract the Godot .pck file using GDRE Tools.

    Command used:
        gdre_tools --headless --recover="<pck_path>" --output-dir=<output_dir>

    GDRE Tools (Godot RE Tools) can unpack Godot 4 .pck files, which contain
    all the game's resources — including the FMOD sound banks we need.

    Returns True on success, False on failure.
    """
    step("Extracting .pck file with GDRE Tools...")

    cmd = [
        gdre_path,
        "--headless",
        f"--recover={pck_path}",
        f"--output-dir={output_dir}",
    ]

    info(f"Running: {' '.join(cmd)}")

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=600,  # 10 minutes should be plenty
        )
    except subprocess.TimeoutExpired:
        error("GDRE Tools timed out after 10 minutes. The .pck file may be very large.")
        return False
    except FileNotFoundError:
        error(f"Could not run GDRE Tools at: {gdre_path}")
        error("Make sure the path is correct and the file is executable.")
        return False
    except Exception as e:
        error(f"Unexpected error running GDRE Tools: {e}")
        return False

    if result.returncode != 0:
        error("GDRE Tools failed to extract the .pck file.")
        if result.stderr:
            error(f"GDRE Tools stderr:\n{result.stderr}")
        if result.stdout:
            # Sometimes GDRE prints useful info to stdout even on failure
            info(f"GDRE Tools stdout:\n{result.stdout}")
        return False

    # Check that the output directory actually has content
    if not output_dir.exists() or not any(output_dir.iterdir()):
        error(f"GDRE Tools reported success, but the output directory is empty: {output_dir}")
        return False

    success(f"Extraction complete. Files saved to: {output_dir}")
    return True


# ---------------------------------------------------------------------------
# Step 5: Find the sfx.bank file in the extracted files
# ---------------------------------------------------------------------------

def find_sfx_bank(extraction_dir: Path) -> Optional[Path]:
    """
    Find the sfx.bank file inside the extracted game files.

    After GDRE extraction, FMOD sound banks are typically at:
        extraction/banks/desktop/sfx.bank

    But the exact path might vary between game versions, so we also do
    a recursive search for any file named 'sfx.bank'.
    """
    # Primary expected path
    bank_path = extraction_dir / "banks" / "desktop" / "sfx.bank"
    if bank_path.exists():
        size_mb = bank_path.stat().st_size / (1024 * 1024)
        success(f"Found sfx.bank: {bank_path} ({size_mb:.1f} MB)")
        return bank_path

    # Recursive fallback search
    info("sfx.bank not at expected path — searching recursively...")
    bank_files = list(extraction_dir.rglob("sfx.bank"))
    if bank_files:
        bank_path = bank_files[0]
        size_mb = bank_path.stat().st_size / (1024 * 1024)
        success(f"Found sfx.bank at: {bank_path} ({size_mb:.1f} MB)")
        return bank_path

    # Last resort: find any .bank file
    bank_files = list(extraction_dir.rglob("*.bank"))
    if bank_files:
        warn(f"Could not find 'sfx.bank' specifically, but found {len(bank_files)} .bank file(s):")
        for bf in bank_files:
            warn(f"  - {bf}")
        # If there's only one, use it; otherwise ask the user
        if len(bank_files) == 1:
            return bank_files[0]
        else:
            # Try to find one with "sfx" in the name
            sfx_banks = [b for b in bank_files if "sfx" in b.name.lower()]
            if len(sfx_banks) == 1:
                return sfx_banks[0]
            error("Multiple .bank files found. Please specify which one to use.")
            return None

    error("No .bank files found in the extracted game data.")
    error("This might mean the game version has changed its audio format,")
    error("or the extraction did not complete correctly.")
    return None


# ---------------------------------------------------------------------------
# Step 6: List subsongs in the .bank file using vgmstream
# ---------------------------------------------------------------------------

# Regex to parse vgmstream's subsong listing output.
# vgmstream-cli with -l (or just running it on a .bank) prints info like:
#   "name: sts2_sfx_VO_merchant_hello  stream #: 42"
# or similar. The exact format varies by version, so we use a flexible regex.
# We also handle the case where vgmstream prints a table with subsong names.

def list_subsongs(vgmstream_path: str, bank_path: Path) -> List[Tuple[int, str]]:
    """
    List all subsongs in a .bank file using vgmstream-cli.

    FMOD .bank files contain multiple "subsongs" — individual audio clips.
    vgmstream can list them and their names. We need to find the ones
    related to the merchant.

    The subsong naming convention for StS2 is:
        sts2_sfx_VO_merchant_<action>
    e.g., sts2_sfx_VO_merchant_greeting, sts2_sfx_VO_merchant_purchase, etc.

    Returns a list of (subsong_index, subsong_name) tuples.
    """
    step("Listing subsongs in sfx.bank with vgmstream...")

    # vgmstream-cli -l <file>  lists subsongs
    # Some versions use -L or --list; we try a few options.
    cmd = [vgmstream_path, "-l", str(bank_path)]
    info(f"Running: {' '.join(cmd)}")

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    except subprocess.TimeoutExpired:
        error("vgmstream timed out while listing subsongs.")
        return []
    except FileNotFoundError:
        error(f"Could not run vgmstream at: {vgmstream_path}")
        return []
    except Exception as e:
        error(f"Unexpected error running vgmstream: {e}")
        return []

    # Combine stdout and stderr — vgmstream sometimes prints info to stderr
    output = (result.stdout or "") + "\n" + (result.stderr or "")

    if result.returncode != 0 and not output.strip():
        error("vgmstream failed to list subsongs and produced no output.")
        return []

    # Parse the output to extract subsong names and indices.
    # vgmstream's listing format varies by version. Common patterns:
    #
    # Pattern 1 (older versions):
    #   "stream #: 1   name: sts2_sfx_VO_merchant_greeting"
    #
    # Pattern 2 (newer versions with -l):
    #   "  1: sts2_sfx_VO_merchant_greeting"
    #
    # Pattern 3 (metadata mode):
    #   "subsong 1: sts2_sfx_VO_merchant_greeting"
    #
    # We use multiple regex patterns and collect all matches.

    subsongs: List[Tuple[int, str]] = []

    # Pattern 1: "stream #: <n> ... name: <name>"
    for m in re.finditer(r"stream\s*#:\s*(\d+).*?name:\s*(\S+)", output, re.IGNORECASE):
        idx = int(m.group(1))
        name = m.group(2).strip().strip('"').strip("'")
        subsongs.append((idx, name))

    # Pattern 2: "<n>: <name>" (where name contains typical VO chars)
    if not subsongs:
        for line in output.splitlines():
            line = line.strip()
            # Match lines like "  42: sts2_sfx_VO_merchant_hello"
            m = re.match(r"(\d+):\s*(sts2_sfx_\S+)", line)
            if m:
                idx = int(m.group(1))
                name = m.group(2).strip().strip('"').strip("'")
                subsongs.append((idx, name))

    # Pattern 3: "subsong <n>: <name>"
    if not subsongs:
        for m in re.finditer(r"subsong\s+(\d+):\s*(\S+)", output, re.IGNORECASE):
            idx = int(m.group(1))
            name = m.group(2).strip().strip('"').strip("'")
            subsongs.append((idx, name))

    # Pattern 4: broader — look for any line containing "sts2" and a number
    if not subsongs:
        for line in output.splitlines():
            # Find a number followed by something that looks like a subsong name
            m = re.search(r"(\d+).*?(sts2_\S+)", line)
            if m:
                idx = int(m.group(1))
                name = m.group(2).strip().strip('"').strip("'")
                subsongs.append((idx, name))

    if not subsongs:
        # If we still haven't found anything, dump the raw output for debugging
        error("Could not parse subsong listing from vgmstream output.")
        error("Raw vgmstream output (first 2000 chars):")
        error(output[:2000])
        error("")
        error("This may indicate a different vgmstream version or .bank format.")
        error("You can try running vgmstream manually to inspect the bank:")
        error(f'  "{vgmstream_path}" -l "{bank_path}"')
        return []

    # De-duplicate by subsong index (keep first occurrence)
    seen_indices = set()
    unique_subsongs: List[Tuple[int, str]] = []
    for idx, name in subsongs:
        if idx not in seen_indices:
            seen_indices.add(idx)
            unique_subsongs.append((idx, name))

    info(f"Found {len(unique_subsongs)} total subsongs in sfx.bank.")
    return unique_subsongs


# ---------------------------------------------------------------------------
# Step 7: Filter for merchant voice lines
# ---------------------------------------------------------------------------

def filter_merchant_subsongs(subsongs: List[Tuple[int, str]]) -> List[Tuple[int, str]]:
    """
    Filter the subsong list to only include merchant voice lines.

    Merchant voice events are named like:
        sts2_sfx_VO_merchant_<action>

    We match case-insensitively on "merchant" in the subsong name.
    """
    merchant_subsongs = [
        (idx, name)
        for idx, name in subsongs
        if "merchant" in name.lower()
    ]

    if not merchant_subsongs:
        # Maybe the naming convention is different — show some VO subsongs for debugging
        vo_subsongs = [(idx, name) for idx, name in subsongs if "VO" in name or "vo_" in name.lower()]
        if vo_subsongs:
            warn("No subsongs with 'merchant' in the name were found.")
            warn("Here are some VO (voice) subsongs that WERE found, for reference:")
            for idx, name in vo_subsongs[:20]:
                warn(f"  [{idx}] {name}")
            warn("You may need to manually identify merchant lines from the list above.")
        else:
            warn("No VO subsongs were found at all. The bank may not contain voice audio,")
            warn("or the naming convention may have changed in this game version.")

    return merchant_subsongs


# ---------------------------------------------------------------------------
# Step 8: Decode subsongs to .wav using vgmstream
# ---------------------------------------------------------------------------

def decode_subsong(
    vgmstream_path: str,
    bank_path: Path,
    subsong_index: int,
    output_dir: Path,
    subsong_name: str,
) -> Optional[Path]:
    """
    Decode a single subsong from the .bank file to a .wav file.

    vgmstream command:
        vgmstream-cli -s <subsong_index> -i -o "?n.wav" <bank_path>

    The -s flag selects the subsong, -i means ignore errors on other subsongs,
    and "?n.wav" tells vgmstream to use the subsong's internal name for the
    output filename (with .wav extension).

    We override the output directory by running vgmstream with the output dir
    as the working directory, so the .wav file lands there.

    Returns the path to the decoded .wav file, or None on failure.
    """
    # Sanitize the subsong name for use as a filename
    safe_name = re.sub(r'[^\w\-.]', '_', subsong_name)
    wav_filename = f"{safe_name}.wav"
    wav_path = output_dir / wav_filename

    # vgmstream's -o "?n.wav" uses the internal name. But to have full control
    # over the output path, we use -o with our desired filename.
    # We run vgmstream with cwd=output_dir so the file is created there.
    cmd = [
        vgmstream_path,
        "-s", str(subsong_index),
        "-i",
        "-o", wav_filename,
        str(bank_path),
    ]

    info(f"  Decoding subsong {subsong_index}: {subsong_name} → {wav_filename}")

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120,
            cwd=str(output_dir),
        )
    except subprocess.TimeoutExpired:
        error(f"    Timed out decoding subsong {subsong_index}.")
        return None
    except Exception as e:
        error(f"    Error decoding subsong {subsong_index}: {e}")
        return None

    # vgmstream may return non-zero even on partial success, so we check
    # whether the output file was actually created
    if wav_path.exists() and wav_path.stat().st_size > 0:
        size_kb = wav_path.stat().st_size / 1024
        success(f"    Decoded: {wav_filename} ({size_kb:.1f} KB)")
        return wav_path
    else:
        # Maybe vgmstream used a different filename — check for any new .wav
        # files in the output directory
        error(f"    Expected output file not found: {wav_path}")
        if result.stderr:
            error(f"    vgmstream stderr: {result.stderr.strip()}")
        return None


# ---------------------------------------------------------------------------
# Step 9: Convert .wav to .mp3 using ffmpeg
# ---------------------------------------------------------------------------

def convert_to_mp3(ffmpeg_path: str, wav_path: Path) -> Optional[Path]:
    """
    Convert a .wav file to .mp3 using ffmpeg.

    Command:
        ffmpeg -i <input.wav> -codec:a libmp3lame -qscale:a 2 <output.mp3>

    The -qscale:a 2 setting gives ~190 kbps VBR, which is high quality.

    Returns the path to the .mp3 file, or None on failure.
    """
    mp3_path = wav_path.with_suffix(".mp3")

    cmd = [
        ffmpeg_path,
        "-y",           # Overwrite output file if it exists
        "-i", str(wav_path),
        "-codec:a", "libmp3lame",
        "-qscale:a", "2",
        str(mp3_path),
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    except subprocess.TimeoutExpired:
        warn(f"    ffmpeg timed out converting {wav_path.name}")
        return None
    except Exception as e:
        warn(f"    Error converting {wav_path.name}: {e}")
        return None

    if mp3_path.exists() and mp3_path.stat().st_size > 0:
        size_kb = mp3_path.stat().st_size / 1024
        success(f"    Converted to MP3: {mp3_path.name} ({size_kb:.1f} KB)")
        return mp3_path
    else:
        warn(f"    ffmpeg did not produce output file: {mp3_path}")
        if result.stderr:
            # ffmpeg prints most info to stderr
            warn(f"    ffmpeg stderr (last 500 chars): {result.stderr[-500:]}")
        return None


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

def main() -> int:
    """
    Main entry point. Runs the full extraction pipeline.

    Returns 0 on success, 1 on failure.
    """
    banner()

    # --- Parse command-line arguments ---
    parser = argparse.ArgumentParser(
        description="Extract merchant voice lines from Slay the Spire 2 game files.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Make sure you have GDRE Tools and vgmstream-cli installed.\n"
            "See the script header comments for download links and full instructions."
        ),
    )
    parser.add_argument(
        "--game-path",
        type=str,
        default=None,
        help="Path to the Slay the Spire 2 Steam install directory "
             "(auto-detected if not specified).",
    )
    parser.add_argument(
        "--gdre-path",
        type=str,
        default=None,
        help="Path to the gdre_tools executable (searched on PATH if not specified).",
    )
    parser.add_argument(
        "--vgmstream-path",
        type=str,
        default=None,
        help="Path to the vgmstream-cli executable (searched on PATH if not specified).",
    )
    parser.add_argument(
        "--ffmpeg-path",
        type=str,
        default=None,
        help="Path to the ffmpeg executable (searched on PATH if not specified). "
             "If not found, only .wav files will be produced.",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="merchant_voices",
        help="Directory to save extracted voice files (default: merchant_voices).",
    )
    parser.add_argument(
        "--keep-wav",
        action="store_true",
        help="Keep .wav files even after converting to .mp3 (default: wav is removed if mp3 succeeds).",
    )
    parser.add_argument(
        "--extraction-dir",
        type=str,
        default=None,
        help="Directory for the intermediate .pck extraction (default: a temp dir "
             "named 'sts2_extraction' next to the output dir). Can be reused to skip re-extraction.",
    )
    parser.add_argument(
        "--skip-extraction",
        action="store_true",
        help="Skip the GDRE .pck extraction step. Use this if you've already extracted "
             "the .pck and just want to re-run the audio extraction. "
             "Requires --extraction-dir to point to the existing extraction.",
    )
    args = parser.parse_args()

    # -------------------------------------------------------------------
    # Check for required external tools
    # -------------------------------------------------------------------
    step("Checking for required tools...")

    gdre = find_tool("gdre_tools", args.gdre_path)
    if gdre:
        success(f"GDRE Tools found: {gdre}")
    else:
        if args.skip_extraction:
            warn("GDRE Tools not found, but --skip-extraction was specified. Continuing.")
        else:
            error("GDRE Tools (gdre_tools) was not found on your system or PATH.")
            error("Please install it from: https://github.com/bruvzg/gdsdecomp/releases")
            error("Or specify its path with --gdre-path")
            error("If you've already extracted the .pck, use --skip-extraction with --extraction-dir")
            return 1

    vgmstream = find_tool("vgmstream-cli", args.vgmstream_path)
    if vgmstream:
        success(f"vgmstream-cli found: {vgmstream}")
    else:
        error("vgmstream-cli was not found on your system or PATH.")
        error("Please install it from: https://github.com/vgmstream/vgmstream/releases")
        error("Or specify its path with --vgmstream-path")
        return 1

    ffmpeg = find_tool("ffmpeg", args.ffmpeg_path)
    if ffmpeg:
        success(f"ffmpeg found: {ffmpeg}")
    else:
        warn("ffmpeg was not found. Only .wav files will be produced (no .mp3 conversion).")
        warn("Install ffmpeg from https://ffmpeg.org/download.html for .mp3 output.")

    # -------------------------------------------------------------------
    # Step 1: Find the game install
    # -------------------------------------------------------------------
    step("Locating Slay the Spire 2 install directory...")

    game_path = find_sts2_install(args.game_path)
    if not game_path:
        return 1

    # -------------------------------------------------------------------
    # Step 2: Find the .pck file
    # -------------------------------------------------------------------
    pck_path: Optional[Path] = None
    if not args.skip_extraction:
        pck_path = find_pck_file(game_path)
        if not pck_path:
            return 1

    # -------------------------------------------------------------------
    # Prepare output directories
    # -------------------------------------------------------------------
    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    info(f"Output directory: {output_dir}")

    if args.extraction_dir:
        extraction_dir = Path(args.extraction_dir).resolve()
    else:
        extraction_dir = (output_dir.parent / "sts2_extraction").resolve()

    # -------------------------------------------------------------------
    # Step 3: Extract the .pck file (unless skipped)
    # -------------------------------------------------------------------
    if args.skip_extraction:
        step("Skipping .pck extraction (--skip-extraction specified)")
        if not extraction_dir.exists():
            error(f"Extraction directory does not exist: {extraction_dir}")
            error("Cannot skip extraction — the directory with extracted files was not found.")
            return 1
        info(f"Using existing extraction at: {extraction_dir}")
    else:
        extraction_dir.mkdir(parents=True, exist_ok=True)

        # Check if extraction already has content (maybe from a previous run)
        if extraction_dir.exists() and any(extraction_dir.iterdir()):
            info(f"Extraction directory already has content: {extraction_dir}")
            info("Skipping extraction (use --extraction-dir with an empty/new dir to force re-extraction)")
        else:
            if not gdre:
                error("GDRE Tools is required for extraction but was not found.")
                return 1
            if not extract_pck(gdre, pck_path, extraction_dir):
                error("Failed to extract the .pck file.")
                return 1

    # -------------------------------------------------------------------
    # Step 4: Find sfx.bank
    # -------------------------------------------------------------------
    step("Locating sfx.bank in extracted files...")

    sfx_bank = find_sfx_bank(extraction_dir)
    if not sfx_bank:
        return 1

    # -------------------------------------------------------------------
    # Step 5: List subsongs and filter for merchant
    # -------------------------------------------------------------------
    all_subsongs = list_subsongs(vgmstream, sfx_bank)
    if not all_subsongs:
        error("No subsongs could be listed from sfx.bank.")
        return 1

    merchant_subsongs = filter_merchant_subsongs(all_subsongs)

    if not merchant_subsongs:
        error("No merchant voice lines were found in the sound bank.")
        error("This could mean:")
        error("  1. The merchant's lines use a different naming convention in this game version.")
        error("  2. The voice lines are in a different .bank file.")
        error("  3. The merchant voice lines haven't been added to the game yet.")
        error("")
        error("Try running vgmstream manually to inspect the bank:")
        error(f'  "{vgmstream}" -l "{sfx_bank}"')
        error("And look for any subsong names containing 'merchant' or 'VO'.")
        return 1

    # -------------------------------------------------------------------
    # Step 6: Decode and convert merchant subsongs
    # -------------------------------------------------------------------
    step(f"Decoding {len(merchant_subsongs)} merchant voice line(s)...")

    decoded_wavs: List[Path] = []
    converted_mp3s: List[Path] = []

    for idx, name in merchant_subsongs:
        info(f"\n  Processing: {name} (subsong #{idx})")

        # Decode to .wav
        wav_path = decode_subsong(vgmstream, sfx_bank, idx, output_dir, name)
        if wav_path:
            decoded_wavs.append(wav_path)

            # Convert to .mp3 if ffmpeg is available
            if ffmpeg:
                mp3_path = convert_to_mp3(ffmpeg, wav_path)
                if mp3_path:
                    converted_mp3s.append(mp3_path)
                    # Remove the .wav unless the user asked to keep it
                    if not args.keep_wav:
                        try:
                            wav_path.unlink()
                        except Exception:
                            pass  # Non-critical if deletion fails
        else:
            warn(f"  Failed to decode subsong #{idx} ({name})")

    # -------------------------------------------------------------------
    # Summary
    # -------------------------------------------------------------------
    step("Extraction Summary")
    print()

    print(f"  Total subsongs in sfx.bank : {len(all_subsongs)}")
    print(f"  Merchant voice lines found : {len(merchant_subsongs)}")
    print(f"  Successfully decoded (.wav): {len(decoded_wavs)}")
    if ffmpeg:
        print(f"  Converted to .mp3          : {len(converted_mp3s)}")
    else:
        print(f"  Converted to .mp3          : 0 (ffmpeg not available)")
    print()
    print(f"  Output directory: {output_dir}")
    print()

    if decoded_wavs or converted_mp3s:
        print("  Files produced:")
        # List mp3s first if available, then any remaining wavs
        all_output_files = []
        if converted_mp3s:
            all_output_files.extend(converted_mp3s)
        remaining_wavs = [w for w in decoded_wavs if w.exists()]
        all_output_files.extend(remaining_wavs)

        for f in sorted(all_output_files):
            size_kb = f.stat().st_size / 1024
            print(f"    {f.name:50s}  ({size_kb:.1f} KB)")

        print()
        success("Done! Your merchant voice files are ready to use.")
        if not ffmpeg:
            print()
            warn("Install ffmpeg to also get .mp3 versions (smaller, more compatible).")

        return 0
    else:
        error("No files were successfully extracted. See errors above.")
        return 1


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print()
        warn("Interrupted by user (Ctrl+C). Some files may be incomplete.")
        sys.exit(130)
    except Exception as e:
        error(f"Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)