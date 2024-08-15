# copy certificate to include it in build. added when removed
# `requests` because I wasn't able to avoid getting a HTTP 403.
all: certificate pyinstall

certificate:
	mkdir --parents certifi
	cp venv/lib/python3.*/site-packages/certifi/cacert.pem certifi/

# spec file generated unsing:
# pyinstaller src/main.py --name patricie --onefile --clean --add-data "assets:assets"
pyinstall: certifi
	pyinstaller patricie-linux.spec
