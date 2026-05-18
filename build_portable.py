#!/usr/bin/env python3
"""
build_portable.py — Build single portable .exe (no install needed).

Output: dist/VideoDownloaderPortable.exe

How it works:
  - PyInstaller --onefile bundles Python + all deps + ffmpeg into one exe
  - On launch: extracts to %TEMP% automatically, runs the app
  - On exit:   cleans up %TEMP% automatically
  - Delete exe = everything gone, zero residual files
"""

import subprocess
import sys
import os
import shutil

BASE    = os.path.dirname(os.path.abspath(__file__))
VENV_PY = os.path.join(BASE, "venv", "Scripts", "python.exe")
VENV_PIP = os.path.join(BASE, "venv", "Scripts", "pip.exe")
APP     = "VideoDownloaderPortable"
OUT_EXE = os.path.join(BASE, "dist", f"{APP}.exe")


def hdr(msg: str):
    bar = "-" * 60
    print(f"\n{bar}\n  {msg}\n{bar}")


def go(*cmd, cwd=BASE):
    print(">>>", " ".join(str(c) for c in cmd))
    result = subprocess.run(list(cmd), cwd=cwd)
    if result.returncode != 0:
        sys.exit(f"\nERROR: command failed (exit {result.returncode})")


def main():
    hdr("Video Downloader — Portable Build")

    if not os.path.exists(VENV_PY):
        sys.exit(
            "ERROR: venv not found.\n"
            "Run: python -m venv venv && venv\\Scripts\\pip install -r requirements.txt"
        )

    # Generate icon if missing
    icon = os.path.join(BASE, "icon.ico")
    if not os.path.exists(icon):
        hdr("Generating app icon")
        go(VENV_PY, os.path.join(BASE, "make_icon.py"))

    hdr("Step 1 / 2 — Installing PyInstaller")
    go(VENV_PIP, "install", "pyinstaller", "pyinstaller-hooks-contrib", "-q")

    hdr("Step 2 / 2 — Building portable exe (this takes several minutes)")

    # Clean previous build artifacts
    for folder in ("build",):
        p = os.path.join(BASE, folder)
        if os.path.exists(p):
            shutil.rmtree(p)

    prev = os.path.join(BASE, "dist", f"{APP}.exe")
    if os.path.exists(prev):
        os.remove(prev)

    spec = os.path.join(BASE, f"{APP}.spec")
    if os.path.exists(spec):
        os.remove(spec)

    cmd = [
        VENV_PY, "-m", "PyInstaller",
        "--noconfirm",
        "--onefile",           # Everything in a single .exe
        "--windowed",          # No console window
        "--name", APP,
        "--icon", icon,
        "--collect-all", "yt_dlp",
        "--collect-all", "instaloader",
        "--collect-all", "imageio_ffmpeg",
        "--hidden-import", "PIL._tkinter_finder",
        "--hidden-import", "tkinter",
        "--hidden-import", "tkinter.scrolledtext",
        "--hidden-import", "tkinter.filedialog",
        "--hidden-import", "json",
        "--hidden-import", "threading",
        "main.py",
    ]

    go(*cmd)

    if not os.path.exists(OUT_EXE):
        sys.exit(f"ERROR: expected output at {OUT_EXE}")

    mb = os.path.getsize(OUT_EXE) / 1048576
    print(f"\n{'='*60}")
    print(f"  Portable exe ready!")
    print(f"  {OUT_EXE}")
    print(f"  Size: {mb:.0f} MB")
    print()
    print(f"  HOW TO USE:")
    print(f"    - Copy VideoDownloaderPortable.exe anywhere")
    print(f"    - Double-click to run (first launch takes ~15s to unpack)")
    print(f"    - Delete the exe = gone, no leftover files")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
