
@echo off
rem スクリプトが置かれている場所をカレントディレクトリにする。
cd /d %~dp0

call ./venv/Scripts/activate
rem 「test」内の「sub_test」フォルダ（ディレクトリ）へ移動
cd libs

python game_pad_connect.py
pause