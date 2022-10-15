
@echo off
cd /d %~dp0

call ./venv/Scripts/activate
cd libs

python game_pad_connect.py
pause