@echo off
title Video Downloader — Build Installer
echo.
echo  ============================================================
echo    Video Downloader — Installer Builder
echo  ============================================================
echo.
echo  This will:
echo    1. Install PyInstaller
echo    2. Bundle the app into a standalone executable
echo    3. Install Inno Setup (if not present)
echo    4. Compile VideoDownloaderSetup.exe
echo.
echo  Expected build time: 3-10 minutes
echo  Output: installer_output\VideoDownloaderSetup.exe
echo.
pause

"%~dp0venv\Scripts\python.exe" "%~dp0build.py"

echo.
if %errorlevel% == 0 (
    echo  Build completed successfully.
    echo  Installer: installer_output\VideoDownloaderSetup.exe
) else (
    echo  Build failed. See errors above.
)
echo.
pause
