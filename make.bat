:: spec fire generated using pyinstaller src/main.py --noconsole --name PatricieWindows --onefile --clean --add-data "assets:assets" --icon assets/patricie.ico
md certifi
copy venvw\Lib\site-packages\certifi\cacert.pem certifi\
pyinstaller PatricieWindows.spec
