@echo off
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0install.ps1" -Payload "%~dp0payload.zip"
exit /b %errorlevel%
