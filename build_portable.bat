@echo off
title Video Downloader — Build Portable EXE
echo.
echo  ============================================================
echo    Video Downloader — Portable Build
echo  ============================================================
echo.
echo  Builds a single VideoDownloaderPortable.exe
echo  No installation needed — copy anywhere and run.
echo.
echo  NOTE: First launch takes 10-20 seconds (unpacking).
echo        Subsequent launches are the same speed.
echo.
echo  Expected build time: 5-15 minutes
echo  Output: dist\VideoDownloaderPortable.exe
echo.
pause

"%~dp0venv\Scripts\python.exe" "%~dp0build_portable.py"

echo.
if %errorlevel% == 0 (
    echo  Build completed!
    echo  File: dist\VideoDownloaderPortable.exe
    start "" explorer "%~dp0dist"
) else (
    echo  Build failed. See errors above.
)
echo.
pause
