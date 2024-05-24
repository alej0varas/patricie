release:
	pyinstaller src/main.py --add-data "assets:assets" --onefile --clean
