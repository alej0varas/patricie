# copy certificate to include it in build. added when removed
# `requests` because I wasn't able to avoid getting a HTTP 403.
SHELL = /bin/bash

# to be run on the host before `make all`. because of the permissions
# of the shared folder inside the virtual machine the `lib64`
# directory can't be created by `venv`
pre-all:
	rm -rf venvl
	mkdir -p venvl/lib64

# to be run in the virtualmachine after `make pre-all`
all: prepare certificate pyinstall

prepare:
	python3 -m venv --copies venvl
	source venvl/bin/activate
	venvl/bin/python -m pip install -r requirements.txt -r requirements-dev.txt

certificate:
	mkdir --parents certifi
	cp venvl/lib/python3.*/site-packages/certifi/cacert.pem certifi/

# spec file generated unsing:
# pyinstaller src/main.py --name patricie --onefile --clean --add-data "assets:assets"
pyinstall: certifi
	venvl/bin/pyinstaller patricie-linux.spec
