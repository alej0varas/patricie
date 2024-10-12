:: spec fire generated using pyinstaller src/main.py --noconsole --name PatricieWindows --onefile --clean --add-data "assets:assets" --icon assets/patricie.ico
:: before runing make.bat change to ...
:: x:
rmdir /S /Q venvw
Python.exe -m venv venvw
venvw\Scripts\python.exe -m pip install --upgrade pip
venvw\Scripts\python.exe -m pip install -r requirements.txt -r requirements-dev.txt
md certifi
copy venvw\Lib\site-packages\certifi\cacert.pem certifi\
venvw\Scripts\pyinstaller.exe "PatricieWindows.spec"
