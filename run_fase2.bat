@echo off
setlocal
set ROOT=%~dp0
"%ROOT%work\.venv\Scripts\python.exe" -m kenshi_save_editor %*
