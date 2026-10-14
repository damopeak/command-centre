@echo off
cd /d "%~dp0"
echo Log in to Invenno in the window that opens. It closes by itself when you are in.
python invenno.py --login
pause
