SHELL = /bin/bash

#
# only for build (inside virtual machine)
#
all: prepare pyinstall

prepare:
	rm -rf ../venvl
	python3 -m venv --copies ../venvl
	../venvl/bin/python -m pip install -r requirements-build.txt

pyinstall:
	../venvl/bin/pyinstaller patricie-linux.spec
#
# end build
#

#
# local
#
createvenv:
	rm -rf venv
	python -m venv --copies venv
	./venv/bin/python -m pip install --upgrade pip
	./venv/bin/python -m pip install -r requirements-dev.txt
#
# end local
#
