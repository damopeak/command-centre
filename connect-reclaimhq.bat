@echo off
cd /d "%~dp0"
echo Log in to ReclaimHQ in the window that opens. It closes by itself when you are in.
python reclaim.py --login
pause
