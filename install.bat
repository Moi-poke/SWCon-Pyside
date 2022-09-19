@echo off
rem スクリプトが置かれている場所をカレントディレクトリにする。
cd /d %~dp0

echo Please install python 3.10 before installation
pause
rem 念のためvirtualenvのインストールとpipのアップグレードを行う。
py -3.10 -m pip install virtualenv
py -3.10 -m pip install --upgrade pip

rem venvの環境を構築する。
py -3.10 -m venv venv
call ./venv/Scripts/activate

py -3.10 -m pip install --upgrade pip
rem 各パッケージをインストール
pip install -r requirements.txt
echo Installation complete
pause