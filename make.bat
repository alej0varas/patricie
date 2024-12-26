:: before runing make.bat change to ...
:: x:
del dist\Patricie.exe
rmdir /S /Q venvw
Python.exe -m venv venvw
venvw\Scripts\python.exe -m pip install --upgrade pip
venvw\Scripts\python.exe -m pip install -r requirements-build.txt
venvw\Scripts\pyinstaller.exe "PatricieWindows.spec"
