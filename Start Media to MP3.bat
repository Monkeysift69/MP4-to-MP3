@echo off
cd /d "%~dp0"
pythonw media_to_mp3.py
if errorlevel 1 (
  echo The application could not start. Make sure Python is installed.
  pause
)
