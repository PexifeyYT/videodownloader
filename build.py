#!/usr/bin/env python3
"""
Video Downloader — Installer Builder
=====================================
Double-click build.bat or run:
    .\\venv\\Scripts\\python build.py

Outputs:  installer_output/VideoDownloaderSetup.exe
"""

import subprocess
import sys
import os
import shutil
import textwrap
import urllib.request

BASE     = os.path.dirname(os.path.abspath(__file__))
VENV_PY  = os.path.join(BASE, "venv", "Scripts", "python.exe")
VENV_PIP = os.path.join(BASE, "venv", "Scripts", "pip.exe")
APP      = "VideoDownloader"
DIST     = os.path.join(BASE, "dist", APP)
OUT_DIR  = os.path.join(BASE, "installer_output")
ISS_FILE = os.path.join(BASE, "setup.iss")

INNO_PATHS = [
    r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
    r"C:\Program Files\Inno Setup 6\ISCC.exe",
    os.path.expanduser(r"~\AppData\Local\Programs\Inno Setup 6\ISCC.exe"),
]
INNO_URL = "https://files.jrsoftware.org/is/6/innosetup-6.3.3.exe"


# ── Helpers ───────────────────────────────────────────────────────────────────

def hdr(msg: str):
    bar = "─" * 60
    print(f"\n{bar}\n  {msg}\n{bar}")


def go(*cmd, cwd=BASE):
    print(">>>", " ".join(str(c) for c in cmd))
    result = subprocess.run(list(cmd), cwd=cwd)
    if result.returncode != 0:
        sys.exit(f"\nERROR: command failed with code {result.returncode}")


def find_iscc() -> str | None:
    for p in INNO_PATHS:
        if os.path.exists(p):
            return p
    return shutil.which("ISCC")


def get_iscc() -> str | None:
    p = find_iscc()
    if p:
        return p

    hdr("Auto-installing Inno Setup")

    # Try winget (Windows 11 / updated Win 10)
    try:
        print("Trying winget...")
        subprocess.run(
            ["winget", "install", "--id", "JRSoftware.InnoSetup",
             "--silent", "--accept-source-agreements", "--accept-package-agreements"],
            check=True, timeout=180
        )
        p = find_iscc()
        if p:
            return p
    except Exception as e:
        print(f"winget unavailable: {e}")

    # Direct download fallback
    tmp = os.path.join(BASE, "_inno_setup_tmp.exe")
    try:
        print(f"Downloading Inno Setup…")

        def _progress(blocks, block_size, total):
            done = min(blocks * block_size, total)
            pct  = done / total * 100 if total > 0 else 0
            print(f"\r  {pct:5.1f}%  {done/1048576:.1f} / {total/1048576:.1f} MB",
                  end="", flush=True)

        urllib.request.urlretrieve(INNO_URL, tmp, _progress)
        print()
        print("Running Inno Setup installer (silent)…")
        subprocess.run(
            [tmp, "/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART", "/CURRENTUSER"],
            check=True
        )
        return find_iscc()
    except Exception as e:
        print(f"Download failed: {e}")
        return None
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)


# ── Build steps ───────────────────────────────────────────────────────────────

def step_pyinstaller():
    hdr("Step 1 / 3 — Installing PyInstaller")
    go(VENV_PIP, "install", "pyinstaller", "pyinstaller-hooks-contrib", "-q")


def step_build_exe():
    hdr("Step 2 / 3 — Building executable (this takes a few minutes)")

    for folder in ("dist", "build"):
        p = os.path.join(BASE, folder)
        if os.path.exists(p):
            print(f"Cleaning {folder}/…")
            shutil.rmtree(p)
    # clean leftover spec
    spec = os.path.join(BASE, f"{APP}.spec")
    if os.path.exists(spec):
        os.remove(spec)

    cmd = [
        VENV_PY, "-m", "PyInstaller",
        "--noconfirm",
        "--onedir",
        "--windowed",
        "--name", APP,
        "--collect-all", "yt_dlp",
        "--collect-all", "instaloader",
        "--collect-all", "imageio_ffmpeg",
        "--hidden-import", "PIL._tkinter_finder",
        "--hidden-import", "tkinter",
        "--hidden-import", "tkinter.scrolledtext",
        "--hidden-import", "tkinter.filedialog",
        "--hidden-import", "json",
        "--hidden-import", "threading",
    ]

    icon = os.path.join(BASE, "icon.ico")
    if os.path.exists(icon):
        cmd += ["--icon", icon]

    cmd.append("main.py")
    go(*cmd)

    if not os.path.isdir(DIST):
        sys.exit(f"ERROR: expected build output at {DIST}")

    print(f"\nBuild OK → {DIST}")


def step_installer():
    hdr("Step 3 / 3 — Creating Windows installer")
    os.makedirs(OUT_DIR, exist_ok=True)

    # Write Inno Setup script
    iss = textwrap.dedent(f"""\
        [Setup]
        AppName=Video Downloader
        AppVersion=1.0
        AppPublisher=Video Downloader
        DefaultDirName={{autopf}}\\VideoDownloader
        DefaultGroupName=Video Downloader
        AllowNoIcons=yes
        OutputDir={OUT_DIR}
        OutputBaseFilename=VideoDownloaderSetup
        Compression=lzma2/ultra64
        SolidCompression=yes
        WizardStyle=modern
        PrivilegesRequired=lowest
        ArchitecturesAllowed=x64compatible
        ArchitecturesInstallIn64BitMode=x64compatible
        SetupIconFile={os.path.join(BASE, "icon.ico")}

        [Languages]
        Name: "english"; MessagesFile: "compiler:Default.isl"

        [Tasks]
        Name: desktopicon; Description: "Create a &desktop shortcut"; GroupDescription: "Additional icons:"; Flags: checkedonce

        [Files]
        Source: "{DIST}\\*"; DestDir: "{{app}}"; Flags: ignoreversion recursesubdirs createallsubdirs

        [Icons]
        Name: "{{group}}\\Video Downloader";         Filename: "{{app}}\\{APP}.exe"
        Name: "{{group}}\\Uninstall Video Downloader"; Filename: "{{uninstallexe}}"
        Name: "{{userdesktop}}\\Video Downloader"; Filename: "{{app}}\\{APP}.exe"; Tasks: desktopicon

        [Run]
        Filename: "{{app}}\\{APP}.exe"; Description: "Launch Video Downloader"; Flags: nowait postinstall skipifsilent
    """)

    with open(ISS_FILE, "w") as f:
        f.write(iss)
    print(f"Inno Setup script: {ISS_FILE}")

    iscc = get_iscc()
    if not iscc:
        print("\n[!] Could not install Inno Setup automatically.")
        print("    Download manually: https://jrsoftware.org/isdl.php")
        print(f"    Then run: ISCC.exe \"{ISS_FILE}\"")
        print(f"\n    Portable executable is ready at:")
        print(f"    {DIST}\\{APP}.exe")
        return

    print(f"Compiling installer with: {iscc}")
    go(iscc, ISS_FILE)

    out = os.path.join(OUT_DIR, "VideoDownloaderSetup.exe")
    if os.path.exists(out):
        mb = os.path.getsize(out) / 1048576
        print(f"\n{'='*60}")
        print(f"  Installer ready!")
        print(f"  {out}")
        print(f"  Size: {mb:.0f} MB")
        print(f"  Installs to: Program Files\\VideoDownloader")
        print(f"  Creates desktop shortcut + Start Menu entry")
        print(f"  Includes uninstaller (Add/Remove Programs)")
        print(f"{'='*60}")
    else:
        print(f"\nWARN: expected installer at {out}")


# ── Main ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    hdr("Video Downloader — Installer Builder")

    if not os.path.exists(VENV_PY):
        sys.exit(
            "ERROR: venv not found.\n"
            "Run first:\n"
            "  python -m venv venv\n"
            "  venv\\Scripts\\pip install -r requirements.txt"
        )

    # Generate icon if missing
    icon = os.path.join(BASE, "icon.ico")
    if not os.path.exists(icon):
        hdr("Generating app icon")
        go(VENV_PY, os.path.join(BASE, "make_icon.py"))

    step_pyinstaller()
    step_build_exe()
    step_installer()
