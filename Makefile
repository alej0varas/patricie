release:
	rm -rf ./dist ./build
	pyinstaller src/main.py --name mulpyplayer --onefile --clean --add-data "assets:assets"
