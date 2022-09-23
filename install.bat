@echo off

cd /d %~dp0

echo Please install python 3.10 before installation
pause

py -3.10 -m pip install virtualenv
py -3.10 -m pip install --upgrade pip

py -3.10 -m venv venv
call ./venv/Scripts/activate

py -3.10 -m pip install --upgrade pip
pip install -r requirements.txt
echo Installation complete
pause