@echo off
setlocal
title Media to MP3 Setup
cd /d "%~dp0"

echo ========================================
echo        Media to MP3 - One Click Setup
echo ========================================
echo.

call :refresh_path
call :find_python

if not defined PYTHON_CMD (
  echo Python is not installed. Installing Python 3.13...
  call :require_winget || goto :failed
  winget install --id Python.Python.3.13 --exact --accept-package-agreements --accept-source-agreements
  if errorlevel 1 goto :failed
  call :refresh_path
  call :find_python
)

if not defined PYTHON_CMD (
  echo Python was installed, but Windows has not made it available yet.
  echo Restart Windows, then double-click this file again.
  goto :failed
)

%PYTHON_CMD% -c "import tkinter" >nul 2>&1
if errorlevel 1 (
  echo Python was found, but Tkinter is missing.
  echo Reinstall Python from python.org with the Tcl/Tk option enabled.
  goto :failed
)

where ffmpeg >nul 2>&1
if errorlevel 1 (
  echo FFmpeg is not installed. Installing FFmpeg...
  call :require_winget || goto :failed
  winget install --id Gyan.FFmpeg.Essentials --exact --accept-package-agreements --accept-source-agreements
  if errorlevel 1 goto :failed
  call :refresh_path
)

where ffmpeg >nul 2>&1
if errorlevel 1 (
  echo FFmpeg was installed, but Windows has not made it available yet.
  echo Restart Windows, then double-click this file again.
  goto :failed
)

where ffprobe >nul 2>&1
if errorlevel 1 (
  echo FFprobe is missing from the FFmpeg installation.
  goto :failed
)

echo All dependencies are ready.
if /i "%~1"=="--check-only" (
  echo Setup check completed successfully.
  exit /b 0
)

echo Starting Media to MP3...
start "" %PYTHON_CMD% "%~dp0media_to_mp3.py"
exit /b 0

:find_python
set "PYTHON_CMD="
py -3 -c "import sys" >nul 2>&1
if not errorlevel 1 set "PYTHON_CMD=py -3"
if defined PYTHON_CMD exit /b 0
python -c "import sys" >nul 2>&1
if not errorlevel 1 set "PYTHON_CMD=python"
exit /b 0

:refresh_path
set "PATH=%LOCALAPPDATA%\Microsoft\WinGet\Links;%LOCALAPPDATA%\Microsoft\WindowsApps;%PATH%"
for /d %%D in ("%LOCALAPPDATA%\Programs\Python\Python3*") do set "PATH=%%~fD;%%~fD\Scripts;%PATH%"
exit /b 0

:require_winget
where winget >nul 2>&1
if errorlevel 1 (
  echo Windows Package Manager was not found.
  echo Install or update "App Installer" from the Microsoft Store, then try again.
  exit /b 1
)
exit /b 0

:failed
echo.
echo Setup could not finish. Review the message above, then try again.
pause
exit /b 1
